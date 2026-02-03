from fastapi import FastAPI
from app.routes.issues import router as issues_router

app = FastAPI()

app.include_router(issues_router)