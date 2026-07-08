from typing import Literal

from pydantic import BaseModel, Field


BBox = tuple[float, float, float, float]


class SourceUnit(BaseModel):
    unit_id: str
    type: Literal["text_block", "image_region", "table"] = "text_block"
    text: str = ""
    bbox: BBox | None = None


class SourceFrame(BaseModel):
    source_frame_id: str
    type: Literal["pdf_page"] = "pdf_page"
    index: int
    image_path: str
    width: float | None = None
    height: float | None = None
    text: str = ""
    units: list[SourceUnit] = Field(default_factory=list)


class ExtractedDocument(BaseModel):
    document_id: str
    title: str
    document_type: Literal["pdf"] = "pdf"
    source_frames: list[SourceFrame]

