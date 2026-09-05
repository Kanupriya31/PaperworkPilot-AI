from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Evidence(StrictModel):
    quote: str
    location: str


class ExtractedField(StrictModel):
    id: str
    label: str
    plainLanguage: str
    type: Literal["text", "date", "number", "choice", "signature", "attachment", "other"]
    required: bool
    whyItMatters: str
    profileKey: Literal["fullName", "dateOfBirth", "address", "email", "phone", "none"]
    evidence: Evidence


class ExtractedDocument(StrictModel):
    name: str
    required: bool
    reason: str
    acceptableExamples: list[str]
    evidence: Evidence


class ExtractedWarning(StrictModel):
    severity: Literal["info", "caution", "important"]
    title: str
    detail: str
    evidence: Evidence


class Urgency(StrictModel):
    level: Literal["low", "medium", "high", "unknown"]
    reason: str


class ExtractionResult(StrictModel):
    formTitle: str
    formPurpose: str
    plainLanguageSummary: str
    estimatedTime: str
    urgency: Urgency
    fields: list[ExtractedField]
    documents: list[ExtractedDocument]
    warnings: list[ExtractedWarning]
    nextBestAction: str
    confidenceNote: str


class ResumeRequest(StrictModel):
    action: Literal["approve", "edit", "reject", "stop"]
    note: str = Field(default="", max_length=500)


EXTRACTION_SCHEMA = ExtractionResult.model_json_schema()
