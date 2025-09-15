# backend/models/schemas.py
from pydantic import BaseModel
from typing import List, Optional, Dict

class UploadResponse(BaseModel):
    doc_id: str
    chunks: int

class AskRequest(BaseModel):
    question: str
    top_k: int = 5
    workspace_id: Optional[str] = "default"

class AskResult(BaseModel):
    results: List[dict]

class ChatRequest(BaseModel):
    question: str
    top_k: int = 5

class ChatResult(BaseModel):
    answer: str
    citations: List[Dict]
