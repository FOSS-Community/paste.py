from fastapi import File, UploadFile, HTTPException, status, Request, Form
from fastapi.responses import PlainTextResponse, HTMLResponse, RedirectResponse
import shutil
import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from .utils import generate_uuid, check_file_size_limit

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
    if file.content_type != "text/plain":
        raise HTTPException(detail="Only text/plain is supported",
                            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
    if check_file_size_limit(file.file):
        raise HTTPException(detail="File size is too large",
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
    try:
        uuid = generate_uuid()
        if uuid in large_uuid_storage:
            uuid = generate_uuid()
        path = f"data/{uuid}"
        with open(path, 'wb') as f:
            await shutil.copyfileobj(file.file, f)
            large_uuid_storage.append(uuid)
    except Exception:
        # return {"message": "There was an error uploading the file"}
        raise HTTPException(detail="There was an error uploading the file",
                            status_code=status.HTTP_403_FORBIDDEN)
    finally:
        file.file.close()

    return PlainTextResponse(uuid, status_code=status.HTTP_201_CREATED)


@app.get("/paste/{uuid}")
async def post_as_a_text(uuid):
    path = f"data/{uuid}"
    text = ""
    try:
        with open(path, 'rb') as f:
            text = await f.read()
        if check_file_size_limit(text):
            raise HTTPException(detail="File size is too large",
                                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        else:
            return PlainTextResponse(text)
    except Exception as e:
        print(e)
        raise HTTPException(detail="404: The Requested Resource is not found",
                            status_code=status.HTTP_404_NOT_FOUND)


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
        f"http://paste.fosscu.org/paste/{uuid}", status_code=status.HTTP_303_SEE_OTHER
    )


@app.get("/health", status_code=status.HTTP_200_OK)
async def health() -> dict[str, str]:
    return {"status": "ok"}
