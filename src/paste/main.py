import asyncio
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from logging.config import dictConfig
from pathlib import Path
from typing import Any, Awaitable, Callable, List, Optional, Union

from fastapi import (Depends, FastAPI, File, Form, Header, HTTPException,
                     Query, Request, Response, UploadFile, status)
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (HTMLResponse, JSONResponse, PlainTextResponse,
                               RedirectResponse)
from fastapi.templating import Jinja2Templates
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.util import ClassNotFound
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.responses import Response

from . import __author__, __contact__, __url__, __version__
from .config import get_settings
from .database import Session_Local, get_db
from .logging import LogConfig
from .middleware import LimitUploadSize
from .minio import get_object_data, post_object_data
from .models import Paste
from .schema import (HealthErrorResponse, HealthResponse, PasteCreate,
                     PasteDetails, PasteResponse)
from .utils import _filter_object_name_from_link, extract_uuid

# --------------------------------------------------------------------
# Logger
# --------------------------------------------------------------------

dictConfig(LogConfig())
logger = logging.getLogger("paste")


# --------------------------------------------------------------------
# Background task to check and delete expired URLs
# --------------------------------------------------------------------


async def delete_expired_urls() -> None:
    while True:
        try:

            db: Session = Session_Local()

            current_time = datetime.utcnow()

            # Find and delete expired URLs
            expired_urls = db.query(Paste).filter(Paste.expiresat <= current_time).all()

            for url in expired_urls:
                db.delete(url)

            db.commit()

        except Exception as e:
            logger.error(f"Error in deletion task: {e}")

        finally:
            db.close()

        # Check every minute
        await asyncio.sleep(60)












DESCRIPTION: str = "paste.py 🐍 - A pastebin written in python."

limiter = Limiter(key_func=get_remote_address)
app: FastAPI = FastAPI(
    title="paste.py 🐍",
    version=__version__,
    contact=dict(
        name=__author__,
        url=__url__,
        email=__contact__,
    ),
    license_info=dict(name="MIT", url="https://opensource.org/license/mit/"),
    docs_url=None,
    redoc_url="/docs",
)
app.state.limiter = limiter


def rate_limit_exceeded_handler(
    request: Request, exc: Exception
) -> Union[Response, Awaitable[Response]]:
    if isinstance(exc, RateLimitExceeded):
        return Response(content="Rate limit exceeded", status_code=429)
    return Response(content="An error occurred", status_code=500)


app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> Response:
    # Check if it's an API route
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    # For non-API routes, keep the existing 404 handling
    if exc.status_code == 404:
        user_agent = request.headers.get("user-agent", "")
        is_browser_request = "Mozilla" in user_agent

        if is_browser_request:
            try:
                return templates.TemplateResponse(
                    "404.html", {"request": request}, status_code=404
                )
            except Exception as e:
                logger.error(f"Template error: {e}")
                return PlainTextResponse("404: Template Error", status_code=404)
        else:
            return PlainTextResponse(
                "404: The requested resource was not found", status_code=404
            )

    return PlainTextResponse(str(exc.detail), status_code=exc.status_code)


# Startup event to begin background task
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(delete_expired_urls())


origins: List[str] = ["*"]

BASE_URL: str = get_settings().BASE_URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(LimitUploadSize, max_upload_size=20_000_000)  # ~20MB

BASE_DIR: Path = Path(__file__).resolve().parent

templates: Jinja2Templates = Jinja2Templates(directory=str(Path(BASE_DIR, "templates")))


# --------------------------------------------------------------------
# Root and Health endpoints
# --------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
@limiter.limit("100/minute")
async def indexpage(request: Request) -> Response:
    logger.debug(f"Received request from {request.client.host}")
    logger.info(f"Hit at home page - Method: {request.method}")
    return templates.TemplateResponse("index.html", {"request": request})


@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
    response_model=HealthResponse,
    responses={
        503: {"model": HealthErrorResponse, "description": "Database connection failed"}
    },
)
async def health(db: Session = Depends(get_db)) -> HealthResponse:
    """
    Health check endpoint that verifies database connectivity.
    Returns:
        200 OK: Database is connected and healthy
        503 Service Unavailable: Database connection failed
    """
    try:
        # Measure database response time
        start_time = time.time()
        db.execute(text("SELECT 1"))
        end_time = time.time()

        return HealthResponse(
            db_response_time_ms=round((end_time - start_time) * 1000, 2)
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=HealthErrorResponse(error_message=str(e)).model_dump(),
        )
    finally:
        db.close()


# --------------------------------------------------------------------
# Core paste endpoints in REST order
# --------------------------------------------------------------------


@app.get("/paste/{uuid}")
async def get_paste_data(
    request: Request,
    uuid: str,
    user_agent: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Response:
    try:
        uuid = extract_uuid(uuid)

        data = db.query(Paste).filter(Paste.pasteID == uuid).first()

        content: Optional[str] = None
        extension: Optional[str] = None

        if not data.s3_link:
            content = data.content
            extension = data.extension
        else:
            content = get_object_data(_filter_object_name_from_link(data.s3_link))
            extension = data.extension

        extension = extension[1::] if extension.startswith(".") else extension

        is_browser_request = "Mozilla" in user_agent if user_agent else False

        if not is_browser_request:
            # Return plain text response
            return PlainTextResponse(content)

        logger.info(f"extension: {extension}")

        if extension == "":
            # Guess lexer based on content
            lexer = guess_lexer(content)
        else:
            # Determine lexer based on file extension
            try:
                lexer = get_lexer_by_name(extension, stripall=True)
            except ClassNotFound:
                lexer = get_lexer_by_name("text", stripall=True)  # Default lexer

        formatter = HtmlFormatter(
            style="monokai",  # Dark theme base
            linenos="inline",
            cssclass="highlight",
            nowrap=False,
        )

        highlighted_code: str = highlight(content, lexer, formatter)

        return templates.TemplateResponse(
            "paste.html",
            {
                "request": request,
                "uuid": uuid,
                "highlighted_code": highlighted_code,
                "pygments_css": formatter.get_style_defs(".highlight"),
            },
        )
    except Exception:
        db.rollback()
        raise HTTPException(
            detail="404: The Requested Resource is not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    finally:
        db.close()


@app.post("/file", response_class=PlainTextResponse)
@limiter.limit("100/minute")
async def post_as_a_file(
    request: Request,
    file: UploadFile = File(...),
    expiration: Optional[str] = Query(
        None, description="Expiration time: '1h', '1d', '1w', '1m', or ISO datetime"
    ),
    db: Session = Depends(get_db),
) -> PlainTextResponse:
    try:
        file_extension: Optional[str] = None
        # Extract file extension from the filename
        try:
            if file.filename is not None:
                file_extension = Path(file.filename).suffix
        except Exception:
            file_extension = ""

        # Calculate expiration time if provided
        expiration_time = None
        if expiration:
            current_time = datetime.now(timezone.utc)
            if expiration == "1h":
                expiration_time = current_time + timedelta(hours=1)
            elif expiration == "1d":
                expiration_time = current_time + timedelta(days=1)
            elif expiration == "1w":
                expiration_time = current_time + timedelta(weeks=1)
            elif expiration == "1m":
                expiration_time = current_time + timedelta(days=30)
            else:
                # Try parsing as ISO format datetime
                try:
                    expiration_time = datetime.fromisoformat(
                        expiration.replace("Z", "+00:00")
                    )
                    if expiration_time <= current_time:
                        raise HTTPException(
                            detail="Expiration time must be in the future",
                            status_code=status.HTTP_400_BAD_REQUEST,
                        )
                except ValueError:
                    raise HTTPException(
                        detail="Invalid expiration format. Use '1h', '1d', '1w', '1m', or ISO datetime",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )

        content = await file.read()
        file_content = content.decode("utf-8")

        if len(content) > 102400:
            s3_link: str = post_object_data(file_content)
            file_data = Paste(extension=file_extension, s3_link=s3_link)
            db.add(file_data)
            db.commit()
            db.refresh(file_data)
            _uuid = file_data.pasteID
            return PlainTextResponse(
                f"{BASE_URL}/paste/{_uuid}", status_code=status.HTTP_201_CREATED
            )
        else:
            file_data = Paste(content=file_content, extension=file_extension)
            db.add(file_data)
            db.commit()
            db.refresh(file_data)
            _uuid = file_data.pasteID
            return PlainTextResponse(
                f"{BASE_URL}/paste/{_uuid}", status_code=status.HTTP_201_CREATED
            )

    except Exception as e:
        db.rollback()
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(
            detail=f"There was an error uploading the file",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    finally:
        file.file.close()
        db.close()


@app.delete("/paste/{uuid}", response_class=PlainTextResponse)
async def delete_paste(uuid: str, db: Session = Depends(get_db)) -> PlainTextResponse:
    uuid = extract_uuid(uuid)
    try:
        data = db.query(Paste).filter(Paste.pasteID == uuid).first()
        if data:
            db.delete(data)
            db.commit()
            return PlainTextResponse(f"File successfully deleted {uuid}")
        else:
            raise HTTPException(
                detail="File Not Found", status_code=status.HTTP_404_NOT_FOUND
            )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            logger.error(f"Error deleting paste: {e}"),
            detail=f"There is an error happend.",
            status_code=status.HTTP_409_CONFLICT,
        )
    finally:
        db.close()


# --------------------------------------------------------------------
# Web interface endpoints
# --------------------------------------------------------------------


@app.get("/web", response_class=HTMLResponse)
@limiter.limit("100/minute")
async def web(request: Request) -> Response:
    return templates.TemplateResponse("web.html", {"request": request})


@app.post("/web", response_class=RedirectResponse)
@limiter.limit("100/minute")
async def web_post(
    request: Request,
    content: str = Form(...),
    extension: Optional[str] = Form(None),
    expiration: Optional[str] = Form(None),
    custom_expiry: Optional[str] = Form(None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    try:
        expiration_time = None
        if expiration:
            current_time = datetime.now(timezone.utc)
            if expiration == "1min":
                expiration_time = current_time + timedelta(minutes=1)
            if expiration == "1h":
                expiration_time = current_time + timedelta(hours=1)
            elif expiration == "1d":
                expiration_time = current_time + timedelta(days=1)
            elif expiration == "1w":
                expiration_time = current_time + timedelta(weeks=1)
            elif expiration == "1m":
                expiration_time = current_time + timedelta(days=30)
            elif expiration == "custom" and custom_expiry:
                # Parse the custom expiry datetime string
                try:
                    expiration_time = datetime.fromisoformat(
                        custom_expiry.replace("Z", "+00:00")
                    )
                except ValueError:
                    raise HTTPException(
                        detail="Invalid custom expiry date format",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )

        # Check if the size of the file_content is more than 100 KB
        if len(content) > 102400:
            s3_link: str = post_object_data(content)
            file = Paste(
                extension=extension,
                s3_link=s3_link,
                expiresat=expiration_time,
            )
            db.add(file)
            db.commit()
            db.refresh(file)
            _uuid = file.pasteID
            return RedirectResponse(
                f"{BASE_URL}/paste/{_uuid}", status_code=status.HTTP_303_SEE_OTHER
            )
        else:
            file = Paste(
                content=content, extension=extension, expiresat=expiration_time
            )
            db.add(file)
            db.commit()
            db.refresh(file)
            _uuid = file.pasteID
            return RedirectResponse(
                f"{BASE_URL}/paste/{_uuid}", status_code=status.HTTP_303_SEE_OTHER
            )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            detail=f"There was an error creating the paste: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    finally:
        db.close()


# --------------------------------------------------------------------
# API endpoints in REST order
# --------------------------------------------------------------------


@app.get("/api/paste/{uuid}", response_model=PasteDetails)
@limiter.limit("100/minute")
async def get_paste_details(
    request: Request, uuid: str, db: Session = Depends(get_db)
) -> JSONResponse:
    try:
        uuid = extract_uuid(uuid)
        data = db.query(Paste).filter(Paste.pasteID == uuid).first()
        if data:
            return JSONResponse(
                content=PasteDetails(
                    uuid=uuid,
                    content=data.content,
                    extension=data.extension,
                ).model_dump(),
                status_code=status.HTTP_200_OK,
            )
        else:
            raise HTTPException(
                detail="Paste not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            detail=f"Error retrieving paste",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    finally:
        db.close()


@app.post("/api/paste", response_model=PasteResponse)
@limiter.limit("100/minute")
async def create_paste(
    request: Request, paste: PasteCreate, db: Session = Depends(get_db)
) -> JSONResponse:
    try:

        # Calculate expiration time if provided
        expiration_time = None
        if paste.expiration:
            current_time = datetime.utcnow()
            if isinstance(paste.expiration, str):
                if paste.expiration == "1h":
                    expiration_time = current_time + timedelta(hours=1)
                elif paste.expiration == "1d":
                    expiration_time = current_time + timedelta(days=1)
                elif paste.expiration == "1w":
                    expiration_time = current_time + timedelta(weeks=1)
                elif paste.expiration == "1m":
                    expiration_time = current_time + timedelta(days=30)
            else:
                # If it's a datetime object
                expiration_time = paste.expiration
                if expiration_time <= current_time:
                    raise HTTPException(
                        detail="Expiration time must be in the future",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )

        file_content: bytes = paste.content.encode()

        if len(file_content) > 102400:
            s3_link: str = post_object_data(file_content.decode("utf-8"))
            file = Paste(
                extension=paste.extension,
                s3_link=s3_link,
                expiresat=expiration_time,
            )
            db.add(file)
            db.commit()
            db.refresh(file)
            _uuid = file.pasteID
            return JSONResponse(
                content=PasteResponse(
                    uuid=_uuid, url=f"{BASE_URL}/paste/{_uuid}"
                ).model_dump(),
                status_code=status.HTTP_201_CREATED,
            )
        else:
            file = Paste(
                content=file_content.decode("utf-8"),
                extension=paste.extension,
                expiresat=expiration_time,
            )
            db.add(file)
            db.commit()
            db.refresh(file)
            _uuid = file.pasteID
            return JSONResponse(
                content=PasteResponse(
                    uuid=_uuid, url=f"{BASE_URL}/paste/{_uuid}"
                ).model_dump(),
                status_code=status.HTTP_201_CREATED,
            )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            detail=f"There was an error creating the paste",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    finally:
        db.close()


# --------------------------------------------------------------------
# utility endpoints in REST order
# --------------------------------------------------------------------


@app.get("/languages.json", response_class=JSONResponse)
async def get_languages() -> JSONResponse:
    try:
        with open(Path(BASE_DIR, "languages.json"), "r") as file:
            languages_data: dict = json.load(file)
        return JSONResponse(content=languages_data, status_code=status.HTTP_200_OK)
    except FileNotFoundError:
        raise HTTPException(
            detail="Languages file not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        logger.error(f"Error reading languages file: {e}")
        raise HTTPException(
            detail=f"Error reading languages file",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
