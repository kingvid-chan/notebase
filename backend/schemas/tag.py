"""标签请求/响应 Pydantic 模型。"""

from pydantic import BaseModel, Field


class TagCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)


class TagResponse(BaseModel):
    id: int
    name: str
    user_id: int
    created_at: str

    model_config = {"from_attributes": True}


class TagListResponse(BaseModel):
    tags: list[TagResponse]
