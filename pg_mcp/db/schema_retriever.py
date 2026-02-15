from __future__ import annotations

import re
from typing import List, Set

from pg_mcp.models.schema import DatabaseSchema, TableSchema


class SchemaRetriever:
    """RAG-lite schema retriever based on lexical similarity."""

    def __init__(self, schema: DatabaseSchema) -> None:
        self.schema = schema

    def retrieve_relevant_tables(self, query: str, top_k: int = 5) -> List[TableSchema]:
        """
        Retrieves top-k relevant tables based on keywords in the query.
        Matches keywords against table names, column names, and schemas.
        """
        # Simple keyword extraction: lowercase and split by non-alphanumeric
        keywords = set(re.findall(r"\w+", query.lower()))
        if not keywords:
            return self.schema.tables[:top_k]

        scored_tables = []
        for table in self.schema.tables:
            score = 0
            t_name_lower = table.name.lower()
            s_name_lower = table.schema_name.lower()

            # Table name match (higher weight)
            for kw in keywords:
                if kw in t_name_lower:
                    score += 10
                if kw in s_name_lower:
                    score += 2

            # Column name match
            for col in table.columns:
                c_name_lower = col.name.lower()
                for kw in keywords:
                    if kw in c_name_lower:
                        score += 1

            if score > 0:
                scored_tables.append((score, table))

        # Sort by score descending
        scored_tables.sort(key=lambda x: x[0], reverse=True)
        
        # Return top-k tables
        return [t for _, t in scored_tables[:top_k]]
