import json
import os
import shutil
from pathlib import Path
from typing import Any, Awaitable, Callable, List, Optional, Union

from fastapi import (
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
)
from fastapi.templating import Jinja2Templates
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.util import ClassNotFound
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import Response
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exception_handlers import http_exception_handler

from . import __author__, __contact__, __url__, __version__
from .middleware import LimitUploadSize
from .schema import PasteCreate, PasteDetails, PasteResponse
from .utils import _find_without_extension, generate_uuid
from .config import get_settings

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
    """
    Custom exception handler for HTTP exceptions.
    """
    if exc.status_code == 404:
        user_agent = request.headers.get("user-agent", "")
        is_browser_request = "Mozilla" in user_agent

        if is_browser_request:
            try:
                return templates.TemplateResponse(
                    "404.html", {"request": request}, status_code=404
                )
            except Exception as e:
                print(f"Template error: {e}")  # For debugging
                return PlainTextResponse("404: Template Error", status_code=404)
        else:
            return PlainTextResponse(
                "404: The requested resource was not found", status_code=404
            )

    return PlainTextResponse(str(exc.detail), status_code=exc.status_code)


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

large_uuid_storage: List[str] = []

BASE_DIR: Path = Path(__file__).resolve().parent

templates: Jinja2Templates = Jinja2Templates(directory=str(Path(BASE_DIR, "templates")))


@app.post("/file")
@limiter.limit("100/minute")
async def post_as_a_file(
    request: Request, file: UploadFile = File(...)
) -> PlainTextResponse:
    try:
        uuid: str = generate_uuid()
        if uuid in large_uuid_storage:
            uuid = generate_uuid()
        # Extract file extension from the filename
        try:
            file_extension: Optional[str] = None
            if file.filename is not None:
                file_extension = Path(file.filename).suffix[1:]
            path: str = f"data/{uuid}{file_extension}"
        except Exception:
            path = f"data/{uuid}"
        finally:
            val: str = "/".join(path.split("/")[1:])
        with open(path, "wb") as f:
            shutil.copyfileobj(file.file, f)
            large_uuid_storage.append(uuid)
    except Exception:
        raise HTTPException(
            detail="There was an error uploading the file",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    finally:
        file.file.close()
    return PlainTextResponse(val, status_code=status.HTTP_201_CREATED)


@app.get("/paste/{uuid}")
async def get_paste_data(
    request: Request, uuid: str, user_agent: Optional[str] = Header(None)
) -> Response:
    if not "." in uuid:
        uuid = _find_without_extension(uuid)
    path: str = f"data/{uuid}"
    try:
        with open(path, "rb") as f:
            content: str = f.read().decode("utf-8")
            # Check if the request is from a browser
            is_browser_request = "Mozilla" in user_agent if user_agent else False

            if not is_browser_request:
                # Return plain text response
                return PlainTextResponse(content)

            # Get file extension from the filename
            file_extension: str = Path(path).suffix[1:]
            if file_extension == "":
                # Guess lexer based on content
                lexer = guess_lexer(content)
            else:
                # Determine lexer based on file extension
                try:
                    lexer = get_lexer_by_name(file_extension, stripall=True)
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
        raise HTTPException(
            detail="404: The Requested Resource is not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


@app.get("/", response_class=HTMLResponse)
@limiter.limit("100/minute")
async def indexpage(request: Request) -> Response:
    return templates.TemplateResponse("index.html", {"request": request})


@app.delete("/paste/{uuid}", response_class=PlainTextResponse)
async def delete_paste(uuid: str) -> PlainTextResponse:
    path: str = f"data/{uuid}"
    try:
        os.remove(path)
        return PlainTextResponse(f"File successfully deleted {uuid}")
    except FileNotFoundError:
        raise HTTPException(
            detail="File Not Found", status_code=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        raise HTTPException(
            detail=f"The exception is {e}", status_code=status.HTTP_409_CONFLICT
        )


@app.get("/web", response_class=HTMLResponse)
@limiter.limit("100/minute")
async def web(request: Request) -> Response:
    return templates.TemplateResponse("web.html", {"request": request})


@app.post("/web", response_class=PlainTextResponse)
@limiter.limit("100/minute")
async def web_post(
    request: Request, content: str = Form(...), extension: Optional[str] = Form(None)
) -> RedirectResponse:
    try:
        file_content: bytes = content.encode()
        uuid: str = generate_uuid()
        if uuid in large_uuid_storage:
            uuid = generate_uuid()
        if extension:
            uuid_ = uuid + extension
        else:
            uuid_ = uuid
        path: str = f"data/{uuid_}"
        with open(path, "wb") as f:
            f.write(file_content)
            large_uuid_storage.append(uuid_)
    except Exception:
        raise HTTPException(
            detail="There was an error uploading the file",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    return RedirectResponse(
        f"{BASE_URL}/paste/{uuid_}", status_code=status.HTTP_303_SEE_OTHER
    )


@app.get("/health", status_code=status.HTTP_200_OK)
async def health() -> dict[str, str]:
    return {"status": "ok"}


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
        raise HTTPException(
            detail=f"Error reading languages file: {e}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# apis to create and get a paste which returns uuid and url (to be used by SDK)
@app.post("/api/paste", response_model=PasteResponse)
async def create_paste(paste: PasteCreate) -> JSONResponse:
    try:
        uuid: str = generate_uuid()
        if uuid in large_uuid_storage:
            uuid = generate_uuid()

        uuid_with_extension: str = f"{uuid}.{paste.extension}"
        path: str = f"data/{uuid_with_extension}"

        with open(path, "w", encoding="utf-8") as f:
            f.write(paste.content)

        large_uuid_storage.append(uuid_with_extension)

        return JSONResponse(
            content=PasteResponse(
                uuid=uuid_with_extension, url=f"{BASE_URL}/paste/{uuid_with_extension}"
            ).dict(),
            status_code=status.HTTP_201_CREATED,
        )
    except Exception as e:
        raise HTTPException(
            detail=f"There was an error creating the paste: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@app.get("/api/paste/{uuid}", response_model=PasteDetails)
async def get_paste_details(uuid: str) -> JSONResponse:
    if not "." in uuid:
        uuid = _find_without_extension(uuid)
    path: str = f"data/{uuid}"

    try:
        with open(path, "r", encoding="utf-8") as f:
            content: str = f.read()

        extension: str = Path(path).suffix[1:]

        return JSONResponse(
            content=PasteDetails(
                uuid=uuid, content=content, extension=extension
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
    except FileNotFoundError:
        raise HTTPException(
            detail="Paste not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        raise HTTPException(
            detail=f"Error retrieving paste: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
