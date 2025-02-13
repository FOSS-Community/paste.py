from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text

from .database import Base
from .utils import generate_uuid


class Paste(Base):
    __tablename__ = "pastes"

    pasteID = Column(String(4), primary_key=True, default=generate_uuid)
    content = Column(Text)
    extension = Column(String(50))
    s3_link = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    expiresat = Column(DateTime)
