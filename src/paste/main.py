from fastapi import File, UploadFile, HTTPException, status, Request, Form, FastAPI, Header
from fastapi.responses import PlainTextResponse, HTMLResponse, RedirectResponse, JSONResponse
import shutil
import os
import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from .utils import generate_uuid
from .middleware import LimitUploadSize
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound
from typing import List, Optional, Any

limiter = Limiter(key_func=get_remote_address)
app: FastAPI = FastAPI(title="paste.py 🐍")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

origins: List[str] = ["*"]

BASE_URL: str = r"http://paste.fosscu.org"

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

templates: Jinja2Templates = Jinja2Templates(
    directory=str(Path(BASE_DIR, "templates")))


@app.post("/file")
@limiter.limit("100/minute")
async def post_as_a_file(request: Request, file: UploadFile = File(...)) -> PlainTextResponse:
    try:
        uuid: str = generate_uuid()
        if uuid in large_uuid_storage:
            uuid = generate_uuid()
        # Extract file extension from the filename
        try:
            file_extension: str = Path(file.filename).suffix[1:]
            path: str = f"data/{uuid}.{file_extension}"
        except Exception:
            path = f"data/{uuid}"
        finally:
            val: str = "/".join(path.split("/")[1:])
        with open(path, "wb") as f:
            shutil.copyfileobj(file.file, f)
            large_uuid_storage.append(uuid)
            print(large_uuid_storage)
    except Exception:
        raise HTTPException(
            detail="There was an error uploading the file",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    finally:
        file.file.close()
    return PlainTextResponse(val, status_code=status.HTTP_201_CREATED)


@app.get("/paste/{uuid}")
async def get_paste_data(uuid: str, user_agent: Optional[str] = Header(None)) -> Any:
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
                    lexer = get_lexer_by_name(
                        "text", stripall=True)  # Default lexer
            formatter = HtmlFormatter(
                style="colorful", full=True, linenos="inline", cssclass='code')
            highlighted_code: str = highlight(content, lexer, formatter)

            print(highlighted_code)
            custom_style = """
            .code pre span.linenos {
                color: #999;
                padding-right: 10px;
                -webkit-user-select: none;
                -webkit-touch-callout: none;
                -moz-user-select: none;
                -ms-user-select: none;
                user-select: none;
            }
            
            span {
                font-size: 1.1em !important;
            }

            pre {
                line-height: 1.4 !important;
            }

            .code pre span.linenos::after {
                content: "";
                border-right: 1px solid #999;
                height: 100%;
                margin-left: 10px;
            }

            .code {
                background-color: #fff;
                border: 1.5px solid #ddd;
                border-radius: 5px;
                margin-bottom: 20px;
                overflow: auto;
            }

            pre {
                font-family: 'Consolas','Monaco','Andale Mono','Ubuntu Mono','monospace;' !important;
            }
            """
            response_content: str = f"""
                <html>
                    <head>
                        <title>{uuid}</title>
                        <style>{custom_style}</style>
                        <style>{formatter.get_style_defs('.highlight')}</style>
                    </head>
                    <body>
                        {highlighted_code}
                    </body>
                </html>
                """
            return HTMLResponse(
                content=response_content
            )
    except Exception as e:
        print(e)
        raise HTTPException(
            detail="404: The Requested Resource is not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


@app.get("/", response_class=HTMLResponse)
async def indexpage(request: Request) -> HTMLResponse:
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
async def web(request: Request) -> HTMLResponse:
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
    except Exception as e:
        print(e)
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
