from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.utils.exceptions import DomainError


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(_: Request, error: DomainError):
        return JSONResponse(
            status_code=error.status_code,
            content={"error": error.code, "message": error.message},
        )
