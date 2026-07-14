from typing import Any

from fastapi.responses import JSONResponse


def success_response(message: str, data: Any = None, code: str = "OK") -> dict[str, Any]:
    return {
        "code": str(code),
        "status": "success",
        "message": message,
        "data": data,
    }


def error_response(code: str, message: str, data: Any = None) -> dict[str, Any]:
    return {
        "code": str(code),
        "status": "error",
        "message": message,
        "data": data,
    }


def error_json_response(status_code: int, code: str, message: str, data: Any = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=error_response(code=code, message=message, data=data),
    )
