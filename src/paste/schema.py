from pydantic import BaseModel


class Data(BaseModel):
    input_data: str

class PasteCreate(BaseModel):
    content: str
    extension: Optional[str] = None

class PasteResponse(BaseModel):
    uuid: str
    url: str

class PasteDetails(BaseModel):
    uuid: str
    content: str
    extension: Optional[str]