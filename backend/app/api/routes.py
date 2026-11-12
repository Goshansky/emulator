"""Маршруты REST API эмулятора."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..assembler import AssemblyError, AssemblyResult, assemble
from ..core import Cpu, MachineError, decode
from ..programs import EXAMPLES
from .data_input import DataInputError, parse_initial_data
from .schemas import (
    BuildRequest,
    ErrorDiagnostic,
    ProgramExampleOut,
    SessionResponse,
    StateResponse,
    StepRequest,
    StepResponse,
)
from .sessions import Session, store

router = APIRouter(prefix="/api")


def _error(status: int, diagnostic: ErrorDiagnostic) -> HTTPException:
    return HTTPException(status_code=status, detail=diagnostic.model_dump())


def _assembly_dict(assembly: AssemblyResult) -> dict[str, object]:
    result = assembly.to_dict()
    result["disassembly"] = [decode(word).assembly for word in assembly.instructions]
    return result


def _memory_dict(session: Session) -> dict[str, object]:
    memory = session.cpu.memory()
    return {
        "instructions": memory["instructions"],
        "data": memory["data"],
        "codeSize": len(memory["instructions"]),
        "dataSize": len(memory["data"]),
    }


def _session_or_404(session_id: str) -> Session:
    session = store.get(session_id)
    if session is None:
        raise _error(
            404,
            ErrorDiagnostic(
                code="SESSION_NOT_FOUND",
                message="Сеанс не найден или истёк. Соберите программу заново.",
            ),
        )
    return session


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/programs", response_model=list[ProgramExampleOut])
def programs() -> list[dict[str, object]]:
    return [example.to_dict() for example in EXAMPLES]


@router.post("/sessions", response_model=SessionResponse)
def create_session(request: BuildRequest) -> SessionResponse | JSONResponse:
    try:
        assembly = assemble(request.source)
    except AssemblyError as error:
        diagnostic = error.diagnostic
        raise _error(
            422,
            ErrorDiagnostic(
                code=diagnostic.code,
                message=str(error),
                target="source",
                line=diagnostic.line,
                column=diagnostic.column,
            ),
        ) from error

    try:
        data = parse_initial_data(request.data)
    except DataInputError as error:
        raise _error(
            422,
            ErrorDiagnostic(
                code="INVALID_DATA",
                message=str(error),
                target="data",
                line=error.line,
            ),
        ) from error

    cpu = Cpu()
    try:
        cpu.load({"instructions": list(assembly.instructions), "entryPoint": 0, "data": data})
    except MachineError as error:
        raise _error(
            422,
            ErrorDiagnostic(code=error.code, message=str(error), target="machine"),
        ) from error

    session = store.create(cpu, assembly)
    return SessionResponse(
        sessionId=session.id,
        assembly=_assembly_dict(assembly),
        state=cpu.snapshot().to_dict(),
        memory=_memory_dict(session),
    )


@router.get("/sessions/{session_id}", response_model=StateResponse)
def get_session(session_id: str) -> StateResponse:
    session = _session_or_404(session_id)
    return StateResponse(state=session.cpu.snapshot().to_dict(), memory=_memory_dict(session))


@router.post("/sessions/{session_id}/steps", response_model=StepResponse)
def step_session(session_id: str, request: StepRequest) -> StepResponse:
    session = _session_or_404(session_id)
    with session.lock:
        cpu = session.cpu
        writes: list[dict[str, object]] = []
        executed = 0
        state = cpu.snapshot()
        for _ in range(request.count):
            result = cpu.step()
            state = result.state
            if not result.executed:
                break
            executed += 1
            writes.extend(write.to_dict() for write in result.writes)
    return StepResponse(
        executed=executed > 0,
        executedCount=executed,
        state=state.to_dict(),
        writes=writes,  # type: ignore[arg-type]
    )


@router.post("/sessions/{session_id}/reset", response_model=StateResponse)
def reset_session(session_id: str) -> StateResponse:
    session = _session_or_404(session_id)
    state = session.cpu.reset()
    return StateResponse(state=state.to_dict(), memory=_memory_dict(session))
