from fastapi import File, UploadFile, HTTPException, status, Request, Form
from fastapi.responses import PlainTextResponse, HTMLResponse, RedirectResponse
import shutil
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from .utils import generate_uuid

app = FastAPI(title="paste.py 🐍")

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

templates = Jinja2Templates(directory=str(Path(BASE_DIR, 'templates')))


@app.post("/file")
def post_as_a_file(file: UploadFile = File(...)):
    try:
        uuid = generate_uuid()
        if uuid in large_uuid_storage:
            uuid = generate_uuid()
        path = f"data/{uuid}"
        with open(path, 'wb') as f:
            shutil.copyfileobj(file.file, f)
            large_uuid_storage.append(uuid)
            print(large_uuid_storage)
    except Exception:
        # return {"message": "There was an error uploading the file"}
        raise HTTPException(detail="There was an error uploading the file",
                            status_code=status.HTTP_403_FORBIDDEN)
    finally:
        file.file.close()

    return PlainTextResponse(uuid, status_code=status.HTTP_201_CREATED)


@app.get("/paste/{uuid}")
def post_as_a_text(uuid):
    path = f"data/{uuid}"
    try:
        with open(path, 'rb') as f:
            return PlainTextResponse(f.read())
    except Exception as e:
        print(e)
        raise HTTPException(detail="404: The Requested Resource is not found",
                            status_code=status.HTTP_404_NOT_FOUND)


@app.get("/", response_class=HTMLResponse)
def indexpage(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.delete("/paste/{uuid}", response_class=PlainTextResponse)
def delete_paste(uuid):
    path = f"data/{uuid}"
    try:
        os.remove(path)
        return PlainTextResponse(f"File successfully deleted {uuid}")
    except FileNotFoundError:
        raise HTTPException(detail="File Not Found",
                            status_code=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        raise HTTPException(
            detail=f"The exception is {e}", status_code=status.HTTP_409_CONFLICT)


@app.get("/web", response_class=HTMLResponse)
def web(request: Request):
    return templates.TemplateResponse("web.html", {"request": request})


@app.post("/web", response_class=PlainTextResponse)
def web_post(content: str = Form(...)):
    # print(content)
    # return PlainTextResponse(content=content)
    try:
        file_content = content.encode()
        uuid = generate_uuid()
        if uuid in large_uuid_storage:
            uuid = generate_uuid()
        path = f"data/{uuid}"
        with open(path, 'wb') as f:
            f.write(file_content)
            large_uuid_storage.append(uuid)
    except Exception as e:
        # return {"message": "There was an error uploading the file"}
        print(e)
        raise HTTPException(detail="There was an error uploading the file",
                            status_code=status.HTTP_403_FORBIDDEN)

    return RedirectResponse(f"http://paste.fosscu.org/paste/{uuid}", status_code=status.HTTP_303_SEE_OTHER)
