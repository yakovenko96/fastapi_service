from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class StatusResponse(BaseModel):
    status: str


class User(BaseModel):
    username: str
    disabled: bool | None = None


class UserInDB(User):
    hashed_password: str


class CreateShortRequest(BaseModel):
    original_url: str
    custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = None
    model_config = ConfigDict(
        json_schema_extra={"examples": [
            {
                "original_url": "http://google.com",
                "custom_alias": "abcdef"}]}
    )


class CreateShortResponse(BaseModel):
    short_code: str
    original_url: str


class SearchResponse(BaseModel):
    short_codes: List[str]


class UpdateResponse(BaseModel):
    short_code: str
    original_url: str


class DeleteResponse(BaseModel):
    message: str
