from fastapi import FastAPI
from app.routes.issues import router as issues_router
from app.middleware.timing import timing_middleware

app = FastAPI()

app.middleware("http")(timing_middleware)

app.include_router(issues_router)