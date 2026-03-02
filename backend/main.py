from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.api.scrape import router as scrape_router
from app.api.users import router as users_router
from app.db.init_db import init_db

init_db()
app = FastAPI(title="Cinerex API", version="1.0.0")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"success": False, "data": None, "error": {"code": "VALIDATION_ERROR", "message": str(exc)}},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(_, exc: Exception):
    if hasattr(exc, "detail") and isinstance(exc.detail, dict) and "code" in exc.detail:
        return JSONResponse(status_code=getattr(exc, "status_code", 400), content={"success": False, "data": None, "error": exc.detail})
    return JSONResponse(status_code=500, content={"success": False, "data": None, "error": {"code": "INTERNAL_ERROR", "message": str(exc)}})


app.include_router(health_router)
app.include_router(users_router)
app.include_router(scrape_router)
