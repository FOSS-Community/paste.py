import time
from datetime import datetime
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field


class Data(BaseModel):
    input_data: str


class PasteCreate(BaseModel):
    content: str
    extension: Optional[str] = None
    expiration: Optional[Union[Literal["1h", "1d", "1w", "1m"], datetime]] = None


class PasteResponse(BaseModel):
    uuid: str
    url: str


class PasteDetails(BaseModel):
    uuid: str
    content: str
    extension: Optional[str] = None


class HealthResponse(BaseModel):
    """Schema for successful health check response"""

    status: Literal["ok"] = "ok"
    database: Literal["connected"] = "connected"
    timestamp: float = Field(default_factory=time.time)
    db_response_time_ms: float = Field(ge=0)  # Must be greater than or equal to 0


class HealthErrorResponse(BaseModel):
    """Schema for failed health check response"""

    status: Literal["error"] = "error"
    database: Literal["disconnected"] = "disconnected"
    timestamp: float = Field(default_factory=time.time)
    error_message: str
