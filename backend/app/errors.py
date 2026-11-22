"""RFC 9457 problem-details responses: {type, title, status, detail}."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM_JSON = "application/problem+json"


class Problem(Exception):
    def __init__(
        self, status: int, title: str, detail: str, headers: dict[str, str] | None = None
    ) -> None:
        self.status = status
        self.title = title
        self.detail = detail
        self.headers = headers


def not_found(what: str = "Resource") -> Problem:
    """Also used for objects the viewer may not see, so the API never confirms they exist."""
    return Problem(404, "Not found", f"{what} not found.")


def problem_response(
    status: int,
    title: str,
    detail: str,
    headers: dict[str, str] | None = None,
    **extra: Any,
) -> JSONResponse:
    body = {"type": "about:blank", "title": title, "status": status, "detail": detail, **extra}
    return JSONResponse(body, status_code=status, media_type=PROBLEM_JSON, headers=headers)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(Problem)
    async def handle_problem(_: Request, exc: Problem) -> JSONResponse:
        return problem_response(exc.status, exc.title, exc.detail, exc.headers)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return problem_response(exc.status_code, detail, detail)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Only field names and messages: never echo submitted values such as passwords.
        errors = [
            {"field": ".".join(str(p) for p in e["loc"] if p != "body"), "message": e["msg"]}
            for e in exc.errors()
        ]
        detail = "; ".join(f"{e['field']}: {e['message']}" for e in errors)
        return problem_response(422, "Validation failed", detail, errors=errors)
