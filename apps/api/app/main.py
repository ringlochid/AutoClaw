from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api.router import api_router
from app.db.session import dispose_db_engine


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await dispose_db_engine()


def create_app() -> FastAPI:
    app = FastAPI(title="AutoClaw API", version="0.1.0", lifespan=lifespan)
    app.include_router(api_router)
    return app


app = create_app()
