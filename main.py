import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.database.models as models
from app.database.config import engine
from app.middleware.timing import timing_middleware
from app.routes.issues import router as issues_router

app = FastAPI()

app.middleware("http")(timing_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s",
)

models.Base.metadata.create_all(bind=engine)

app.include_router(issues_router)
