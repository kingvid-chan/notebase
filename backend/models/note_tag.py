from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class NoteTag(Base):
    __tablename__ = "note_tags"

    note_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tag_id: Mapped[int] = mapped_column(Integer, primary_key=True)
