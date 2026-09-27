from fastapi import Request
from fastapi.responses import JSONResponse

class SnakebiteBaseException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class DataNotFoundError(SnakebiteBaseException):
    pass

class InvalidDataError(SnakebiteBaseException):
    pass

class ModelNotLoadedError(SnakebiteBaseException):
    pass

class ClinicalSafetyError(SnakebiteBaseException):
    def __init__(self, message: str, constraint: str):
        self.constraint = constraint
        super().__init__(message)

class DatasetIntegrityError(SnakebiteBaseException):
    pass

class AuthenticationError(SnakebiteBaseException):
    pass

class AuthorizationError(SnakebiteBaseException):
    pass

def create_exception_handlers(app):
    @app.exception_handler(DataNotFoundError)
    async def data_not_found_handler(request: Request, exc: DataNotFoundError):
        return JSONResponse(status_code=404, content={"error_code": "DATA_NOT_FOUND", "message": exc.message, "detail": None})

    @app.exception_handler(InvalidDataError)
    async def invalid_data_handler(request: Request, exc: InvalidDataError):
        return JSONResponse(status_code=400, content={"error_code": "INVALID_DATA", "message": exc.message, "detail": None})

    @app.exception_handler(ModelNotLoadedError)
    async def model_not_loaded_handler(request: Request, exc: ModelNotLoadedError):
        return JSONResponse(status_code=503, content={"error_code": "MODEL_NOT_LOADED", "message": exc.message, "detail": None})

    @app.exception_handler(ClinicalSafetyError)
    async def clinical_safety_handler(request: Request, exc: ClinicalSafetyError):
        return JSONResponse(status_code=400, content={"error_code": "CLINICAL_SAFETY_VIOLATION", "message": exc.message, "detail": exc.constraint})

    @app.exception_handler(DatasetIntegrityError)
    async def dataset_integrity_handler(request: Request, exc: DatasetIntegrityError):
        return JSONResponse(status_code=500, content={"error_code": "DATASET_INTEGRITY_ERROR", "message": exc.message, "detail": None})

    @app.exception_handler(AuthenticationError)
    async def auth_error_handler(request: Request, exc: AuthenticationError):
        return JSONResponse(status_code=401, content={"error_code": "AUTHENTICATION_ERROR", "message": exc.message, "detail": None})

    @app.exception_handler(AuthorizationError)
    async def authz_error_handler(request: Request, exc: AuthorizationError):
        return JSONResponse(status_code=403, content={"error_code": "AUTHORIZATION_ERROR", "message": exc.message, "detail": None})
