from fastapi import FastAPI

import app.database.models as models
from app.database.config import engine
from app.middleware.timing import timing_middleware
from app.routes.issues import router as issues_router

app = FastAPI()

app.middleware("http")(timing_middleware)

models.Base.metadata.create_all(bind=engine)

app.include_router(issues_router)