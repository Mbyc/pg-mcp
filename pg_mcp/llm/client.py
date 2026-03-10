from __future__ import annotations

import logging
from typing import Any

from openai import AsyncOpenAI
from pg_mcp.config import settings
from pg_mcp.llm.prompts import MEANING_VALIDATION_PROMPT, SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from pg_mcp.models.llm import MeaningValidationResponse, SqlGenerationResponse
from pg_mcp.models.schema import TableSchema

logger = logging.getLogger(__name__)

class OpenAIClient:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            base_url=settings.openai_base_url
        )

    async def generate_sql(
        self, 
        query: str, 
        relevant_tables: list[TableSchema],
        error_context: str | None = None
    ) -> SqlGenerationResponse:
        """
        Generates SQL from natural language. 
        Supports error_context for 1-time auto-fix attempts.
        """
        schema_summary = self._build_schema_summary(relevant_tables)
        
        system_content = SYSTEM_PROMPT.format(schema_summary=schema_summary)
        user_content = USER_PROMPT_TEMPLATE.format(query=query)
        
        if error_context:
            user_content += f"\n\nNOTE: The previous SQL failed with this error: {error_context}. Please fix it."

        # DeepSeek and some OpenAI-compatible APIs don't support beta.chat.completions.parse (Structured Outputs)
        # We fall back to regular completions + JSON mode
        fallback_system = (
            system_content
            + "\n\nIMPORTANT: You MUST reply with ONLY a valid JSON object matching this structure: "
            + "{\"sql\": \"...\", \"explanation\": \"...\", \"assumptions\": [], \"confidence\": 0.9, \"clarifying_questions\": []}"
        )

        response = await self.client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": fallback_system},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            timeout=settings.openai_timeout_s
        )
        
        content = (response.choices[0].message.content or "").strip()
        return SqlGenerationResponse.model_validate_json(content)

    async def validate_meaning(
        self,
        query: str,
        sql: str,
        results: list[dict[str, Any]]
    ) -> MeaningValidationResponse:
        """Validates if the result set logically matches the user intent."""
        prompt = MEANING_VALIDATION_PROMPT.format(
            query=query,
            sql=sql,
            row_count=len(results),
            results_json=str(results[:5])
        )
        
        fallback_system = (
            "You are an expert data quality auditor. "
            "IMPORTANT: You MUST reply with ONLY a valid JSON object matching this structure: "
            "{\"matches_intent\": true/false, \"reason\": \"...\", \"suggested_fix\": null}"
        )

        response = await self.client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": fallback_system},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            timeout=settings.openai_timeout_s
        )
        
        content = (response.choices[0].message.content or "").strip()
        return MeaningValidationResponse.model_validate_json(content)

    def _build_schema_summary(self, tables: list[TableSchema]) -> str:
        summary = []
        for table in tables:
            cols = [f"{c.name} ({c.data_type})" for c in table.columns]
            summary.append(f"Table: {table.schema_name}.{table.name}\nColumns: {', '.join(cols)}")
        return "\n\n".join(summary)
