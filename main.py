from fastapi import FastAPI

import app.database.models as models
from app.database.config import engine
from app.middleware.timing import timing_middleware
from fastapi.middleware.cors import CORSMiddleware
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

models.Base.metadata.create_all(bind=engine)

app.include_router(issues_router)