from fastapi import File, UploadFile, HTTPException, status, Request, Form, FastAPI
from fastapi.responses import PlainTextResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound
from pathlib import Path
import os
import shutil

try:
    from .utils import generate_uuid
except ImportError:
    from utils import generate_uuid

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="paste.py 🐍")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

large_uuid_storage = []

BASE_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(directory=str(Path(BASE_DIR, "templates")))


@app.post("/file")
@limiter.limit("100/minute")
async def post_as_a_file(request: Request, file: UploadFile = File(...)):
    try:
        uuid = generate_uuid()
        if uuid in large_uuid_storage:
            uuid = generate_uuid()
        # Extract file extension from the filename
        try:
            file_extension = Path(file.filename).suffix[1:]
            path = f"data/{uuid}.{file_extension}"
        except Exception:
            path = f"data/{uuid}"
        finally:
            val = "/".join(path.split("/")[1:])
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
async def post_as_a_text(uuid):
    path = f"data/{uuid}"
    try:
        with open(path, "rb") as f:
            content = f.read().decode("utf-8")
            # Get file extension from the filename
            file_extension = Path(path).suffix[1:]
            if not file_extension:
                # Guess lexer based on content
                lexer = guess_lexer(content)
            else:
                # Determine lexer based on file extension
                try:
                    lexer = get_lexer_by_name(file_extension, stripall=True)
                except ClassNotFound:
                    lexer = get_lexer_by_name(
                        "text", stripall=True)  # Default lexer
            formatter = HtmlFormatter(style="colorful", full=True)
            highlighted_code = highlight(content, lexer, formatter)

            return HTMLResponse(
                content=highlighted_code
            )
    except Exception as e:
        print(e)
        raise HTTPException(
            detail="404: The Requested Resource is not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


@app.get("/", response_class=HTMLResponse)
async def indexpage(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.delete("/paste/{uuid}", response_class=PlainTextResponse)
async def delete_paste(uuid):
    path = f"data/{uuid}"
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
async def web(request: Request):
    return templates.TemplateResponse("web.html", {"request": request})


@app.post("/web", response_class=PlainTextResponse)
@limiter.limit("100/minute")
async def web_post(request: Request, content: str = Form(...)):
    try:
        file_content = content.encode()
        uuid = generate_uuid()
        if uuid in large_uuid_storage:
            uuid = generate_uuid()
        path = f"data/{uuid}"
        with open(path, "wb") as f:
            f.write(file_content)
            large_uuid_storage.append(uuid)
    except Exception as e:
        print(e)
        raise HTTPException(
            detail="There was an error uploading the file",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    return RedirectResponse(
        f"http://localhost:8080/paste/{uuid}", status_code=status.HTTP_303_SEE_OTHER
    )


@app.get("/health", status_code=status.HTTP_200_OK)
async def health() -> dict[str, str]:
    return {"status": "ok"}
