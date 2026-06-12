from pydantic import BaseModel, Field


class MFASetupResponse(BaseModel):
    secret: str
    provisioning_uri: str
    is_enabled: bool


class MFAVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class MFAStatusResponse(BaseModel):
    is_enabled: bool
