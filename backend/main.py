from pathlib import Path
from typing import List

from dotenv import load_dotenv
load_dotenv()  # must run before llm.py reads ANTHROPIC_API_KEY

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import knowledge_base as kb
import db
import llm
from schemas import (
    ChatRequest, ChatResponse,
    QuizGenerateRequest, QuizGenerateResponse,
    QuizRecordRequest, QuizStatRow,
    SqlLoadRequest, SqlAskRequest, SqlAskResponse,
)

app = FastAPI(title="Benchmark")

# Loosen for local dev / a separately-hosted frontend. Restrict this to your
# actual frontend origin before deploying somewhere public.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/topics")
def topics():
    return {"topics": kb.get_topics()}


# ---------------- DSA Chatbot ----------------

@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    sources = kb.retrieve(req.message, top_n=2)
    if sources:
        context = "\n\n".join(
            f"### {d['title']}\n{d['content']}\nExample:\n{d['code']}" for d in sources
        )
    else:
        context = "(no closely matching notes — answer from general DSA knowledge and say so)"

    system = (
        "You are the tutor behind Benchmark, a concise data-structures-and-algorithms teaching "
        "assistant for an engineering student. Use the CONTEXT when it's "
        "relevant, include one short code example, and keep the explanation "
        "to a few sentences."
    )
    user_prompt = f"CONTEXT:\n{context}\n\nQUESTION: {req.message}"

    try:
        answer = llm.ask(system, user_prompt)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return ChatResponse(answer=answer, sources=[d["title"] for d in sources])


# ---------------- Quiz ----------------

@app.post("/api/quiz/generate", response_model=QuizGenerateResponse)
def generate_quiz(req: QuizGenerateRequest):
    doc = kb.get_doc(req.topic)
    if not doc:
        raise HTTPException(status_code=404, detail="Unknown topic")

    system = (
        "You write multiple-choice quiz questions for a DSA learning app. "
        "Reply with ONLY valid JSON, no markdown fences, no extra text, in "
        'this exact shape: {"questions":[{"question":"...","options":'
        '["...","...","...","..."],"correctIndex":0,"explanation":"..."}]}. '
        "Write exactly 5 questions, medium difficulty, one clearly correct "
        "option each."
    )
    user_prompt = f"Topic: {req.topic}\nReference notes: {doc['content']}"

    try:
        parsed = llm.ask_json(system, user_prompt)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return QuizGenerateResponse(questions=parsed["questions"])


@app.post("/api/quiz/record")
def record_quiz(req: QuizRecordRequest):
    db.record_quiz_result(req.topic, req.correct, req.total)
    return {"ok": True}


@app.get("/api/quiz/stats", response_model=List[QuizStatRow])
def quiz_stats():
    return db.get_quiz_stats()


# ---------------- SQL Assistant ----------------

@app.get("/api/sql/schema")
def sql_schema():
    return {"schema": db.sandbox.schema_text()}


@app.post("/api/sql/load")
def sql_load(req: SqlLoadRequest):
    try:
        db.sandbox.load(req.schema_sql)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True, "schema": db.sandbox.schema_text()}


@app.post("/api/sql/reset")
def sql_reset():
    db.sandbox.reset()
    return {"ok": True, "schema": db.sandbox.schema_text()}


@app.post("/api/sql/ask", response_model=SqlAskResponse)
def sql_ask(req: SqlAskRequest):
    system = (
        "You are a SQL assistant for SQLite. Given a schema and a question "
        'in plain English, reply with ONLY valid JSON, no markdown fences: '
        '{"sql":"...","explanation":"..."}. Prefer a single SELECT query. '
        "Only write INSERT, UPDATE, DELETE, or DDL if the question "
        "explicitly asks to change data."
    )
    user_prompt = f"SCHEMA:\n{db.sandbox.schema_text()}\n\nQUESTION: {req.question}"

    try:
        parsed = llm.ask_json(system, user_prompt)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    sql_text = parsed.get("sql", "")
    explanation = parsed.get("explanation", "")

    if db.sandbox.is_destructive(sql_text):
        return SqlAskResponse(
            sql=sql_text,
            explanation=explanation,
            executed=False,
            warning="This query would change the data, so it wasn't run automatically. Review it, then run it yourself if it looks right.",
        )

    try:
        columns, rows = db.sandbox.execute(sql_text)
    except Exception as exc:
        return SqlAskResponse(
            sql=sql_text,
            explanation=explanation,
            executed=False,
            warning=f"The generated query didn't run: {exc}",
        )

    return SqlAskResponse(
        sql=sql_text, explanation=explanation, executed=True, columns=columns, rows=rows
    )


# ---------------- Static frontend (must be mounted last) ----------------

frontend_dir = Path(__file__).parent.parent / "frontend"
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
