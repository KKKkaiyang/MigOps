import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.exceptions import BizError
from app.core.response import ApiResponse
from app.routers import all_routers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migops")

app = FastAPI(title=f"{settings.APP_NAME} API", version="1.0")


@app.exception_handler(BizError)
async def biz_handler(request: Request, exc: BizError):
    return JSONResponse(
        status_code=200,
        content=ApiResponse(code=exc.code, message=exc.message).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=200,
        content=ApiResponse(
            code=42200, message="参数校验失败", data=exc.errors()
        ).model_dump(),
    )


for r in all_routers:
    app.include_router(r, prefix=settings.API_V1_PREFIX)


@app.get("/health")
def health():
    return {"status": "ok", "db_type": settings.DB_TYPE}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
