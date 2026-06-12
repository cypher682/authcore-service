import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PermissionCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    resource: str = Field(min_length=2, max_length=100)
    action: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class PermissionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    resource: str
    action: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class RoleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class RolePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class RolePermissionAssign(BaseModel):
    permission_id: uuid.UUID


class UserRoleAssign(BaseModel):
    user_id: uuid.UUID
    role_id: uuid.UUID
