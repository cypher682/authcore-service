import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SessionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    device_fingerprint: str
    ip_address: str | None
    user_agent: str | None
    last_active: datetime
    expires_at: datetime
    created_at: datetime
    updated_at: datetime
