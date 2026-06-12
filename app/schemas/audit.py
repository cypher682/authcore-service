import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None
    event_type: str
    ip_address: str | None
    user_agent: str | None
    event_metadata: dict | None
    status: str
    created_at: datetime
    updated_at: datetime
