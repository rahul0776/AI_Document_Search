from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    frontend_origin: str = "http://localhost:3000"

    class Config:
        env_file = ".env"


settings = Settings()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/hello")
def hello():
    return {"message": "Backend is running!"}
