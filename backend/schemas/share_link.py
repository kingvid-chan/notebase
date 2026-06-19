"""分享链接请求/响应 Pydantic 模型。"""

from pydantic import BaseModel, Field


class ShareLinkCreateRequest(BaseModel):
    expires_at: str | None = Field(default=None)


class ShareLinkResponse(BaseModel):
    id: int
    note_id: int
    token: str
    expires_at: str | None
    created_at: str

    model_config = {"from_attributes": True}


class ShareLinkListResponse(BaseModel):
    share_links: list[ShareLinkResponse]
