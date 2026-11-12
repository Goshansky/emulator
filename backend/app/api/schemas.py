"""Pydantic-схемы HTTP API эмулятора."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class BuildRequest(BaseModel):
    source: str = Field(min_length=1)
    data: str = ""


class ProgramExampleOut(BaseModel):
    id: str
    name: str
    description: str
    source: str
    data: str
    resultWords: int | None = None


class ErrorDiagnostic(BaseModel):
    code: str
    message: str
    target: Literal["source", "data", "machine"] = "machine"
    line: int | None = None
    column: int | None = None


class ErrorResponse(BaseModel):
    detail: ErrorDiagnostic


class WriteEventOut(BaseModel):
    kind: Literal["register", "data"]
    address: int
    before: int
    after: int


class SessionResponse(BaseModel):
    sessionId: str
    assembly: dict[str, Any]
    state: dict[str, Any]
    memory: dict[str, Any]


class StateResponse(BaseModel):
    state: dict[str, Any]
    memory: dict[str, Any]


class StepRequest(BaseModel):
    count: int = Field(default=1, ge=1, le=100_000)


class StepResponse(BaseModel):
    executed: bool
    executedCount: int
    state: dict[str, Any]
    writes: list[WriteEventOut]
