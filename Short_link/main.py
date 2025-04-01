import uvicorn
from fastapi import FastAPI
from src.links.api_route import router as api_router
from src.links.schemas import StatusResponse


app = FastAPI(
    title="short_link",
    docs_url="/links/openapi",
    openapi_url="/links/openapi.json",
)


@app.get("/", response_model=StatusResponse, tags=['check app'])
async def root():
    """Проверка работоспособности сервера"""
    return StatusResponse(status="App healthy")


app.include_router(api_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000)
