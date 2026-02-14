from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ColumnSchema(BaseModel):
    name: str
    data_type: str
    is_nullable: bool
    default: Optional[str] = None


class ConstraintSchema(BaseModel):
    name: str
    constraint_type: str
    columns: list[str] = Field(default_factory=list)
    foreign_table: Optional[str] = None
    foreign_columns: list[str] = Field(default_factory=list)


class TableSchema(BaseModel):
    schema: str
    name: str
    kind: str  # table | view | materialized_view
    columns: list[ColumnSchema] = Field(default_factory=list)
    constraints: list[ConstraintSchema] = Field(default_factory=list)


class DatabaseSchema(BaseModel):
    database: str
    tables: list[TableSchema] = Field(default_factory=list)
    loaded_at_epoch_s: float
