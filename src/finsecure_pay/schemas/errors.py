"""Safe request-validation error responses."""

from pydantic import BaseModel


class RequestErrorDetail(BaseModel):
    """Schema error metadata without raw input, context, or exception text."""

    loc: list[str]
    type: str
    msg: str


class RequestErrorResponse(BaseModel):
    """HTTP 422 response for malformed request syntax or structure."""

    detail: list[RequestErrorDetail]
