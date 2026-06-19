"""笔记请求/响应 Pydantic 模型。"""

from pydantic import BaseModel, Field

from backend.schemas.tag import TagResponse


class NoteCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content_markdown: str = Field(default="", max_length=1_048_576)
    tag_ids: list[int] = Field(default_factory=list)


class NoteUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content_markdown: str | None = Field(default=None, max_length=1_048_576)
    is_public: bool | None = None


class NoteResponse(BaseModel):
    id: int
    user_id: int
    title: str
    content_markdown: str
    content_html: str
    is_public: bool
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class NoteDetailResponse(BaseModel):
    note: NoteResponse
    tags: list["TagResponse"]


class NoteListResponse(BaseModel):
    notes: list[NoteResponse]
    total: int
