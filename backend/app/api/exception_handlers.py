from fastapi import Request
from fastapi.exceptions import RequestValidationError

from app.api.errors import AppError, ErrorCode
from app.api.responses import error_json_response


async def app_error_handler(request: Request, exc: AppError):
    return error_json_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        data=exc.data,
    )


async def validation_error_handler(request: Request, exc: RequestValidationError):
    return error_json_response(
        status_code=422,
        code=ErrorCode.VALIDATION_ERROR,
        message="Validation error",
        data={"errors": exc.errors()},
    )


async def internal_error_handler(request: Request, exc: Exception):
    return error_json_response(
        status_code=500,
        code=ErrorCode.INTERNAL_ERROR,
        message="Internal server error",
    )
