from datetime import datetime

from pydantic import BaseModel, Field

from app.models.common import MongoModelConfig, PyObjectId


class SessionInDB(BaseModel):
    model_config = MongoModelConfig

    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId
    refresh_token_hash: str
    expires_at: datetime
    created_at: datetime
    revoked: bool = False
