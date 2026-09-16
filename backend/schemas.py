from typing import List, Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[str]


class QuizGenerateRequest(BaseModel):
    topic: str


class QuizQuestion(BaseModel):
    question: str
    options: List[str]
    correctIndex: int
    explanation: str


class QuizGenerateResponse(BaseModel):
    questions: List[QuizQuestion]


class QuizRecordRequest(BaseModel):
    topic: str
    correct: int
    total: int


class QuizStatRow(BaseModel):
    topic: str
    correct: int
    total: int


class SqlLoadRequest(BaseModel):
    schema_sql: str


class SqlAskRequest(BaseModel):
    question: str


class SqlAskResponse(BaseModel):
    sql: str
    explanation: str
    executed: bool
    warning: Optional[str] = None
    columns: List[str] = []
    rows: List[list] = []
