from __future__ import annotations

from pydantic import BaseModel, Field


class SqlGenerationResponse(BaseModel):
    sql: str = Field(description="The generated PostgreSQL SELECT statement.")
    explanation: str = Field(description="Brief explanation of what the SQL does.")
    assumptions: list[str] = Field(default_factory=list, description="Any assumptions made during generation.")
    confidence: float = Field(ge=0, le=1, description="Confidence score for the generated SQL.")
    clarifying_questions: list[str] = Field(
        default_factory=list, 
        description="Questions to ask the user if the intent is ambiguous."
    )


class MeaningValidationResponse(BaseModel):
    matches_intent: bool = Field(description="Whether the result set matches the user's original intent.")
    reason: str = Field(description="Explanation for the validation result.")
    suggested_fix: str | None = Field(default=None, description="Suggested SQL fix if intent is not matched.")
