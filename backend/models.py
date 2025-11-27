from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from enum import Enum


class GraphicType(str, Enum):
    CHART = "chart"
    DIAGRAM = "diagram"
    CONCEPT = "concept"
    NONE = "none"


class SubmissionStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class SourceType(str, Enum):
    PERSONAL = "personal"
    CLIENT = "client"
    INDUSTRY_REPORT = "industry_report"
    WEB_SOURCE = "web_source"
    ILLUSTRATIVE = "illustrative"


class DataSource(BaseModel):
    dataPoint: str
    value: str
    sourceType: SourceType
    sourceDescription: Optional[str] = None


class ExtractedFact(BaseModel):
    fact: str
    type: str  # statistic, quote, finding, trend
    citation_text: str


class ResearchResult(BaseModel):
    url: str
    source_name: str
    extracted_facts: list[ExtractedFact]
    summary: str
    relevance_score: int
    error: Optional[bool] = None


class SubmissionCreate(BaseModel):
    author: str = Field(..., min_length=1, max_length=100)
    raw_input: str = Field(..., min_length=1)
    graphic_description: Optional[str] = None
    graphic_type: Optional[GraphicType] = None


class SubmissionResponse(BaseModel):
    id: str
    author: str
    raw_input: str
    ai_draft: Optional[str] = None
    graphic_description: Optional[str] = None
    graphic_type: Optional[str] = None
    graphic_data: Optional[str] = None
    status: str
    created_at: str
    reviewed_at: Optional[str] = None
    data_sources: Optional[Any] = None  # JSONB field
    research_urls: Optional[Any] = None  # JSONB field

    class Config:
        from_attributes = True


class SubmissionListResponse(BaseModel):
    submissions: list[SubmissionResponse]


class ApproveRequest(BaseModel):
    edited_post: str = Field(..., min_length=1, max_length=3000)


class RejectRequest(BaseModel):
    reason: Optional[str] = None


class RegenerateImageRequest(BaseModel):
    feedback: str = Field(..., min_length=1, max_length=1000)


class RegenerateImageResponse(BaseModel):
    new_image_data: str


class GenerateVariationsResponse(BaseModel):
    variations: list[str]  # List of base64-encoded images


class SelectVariationRequest(BaseModel):
    image_data: str  # The selected base64-encoded image


class SuccessResponse(BaseModel):
    success: bool = True
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
