# Benchmark — measure what you actually know

A small full-stack app with three modules:

- **Learn** — retrieval-augmented Q&A over a curated DSA notes library (keyword/tag-overlap retrieval, then Claude answers using the retrieved notes).
- **Calibrate** — generates a 5-question multiple-choice quiz per topic on demand, with instant feedback and a persistent calibration report (accuracy by topic).
- **Query Bench** — turns a plain-English question into SQL against a real SQLite database, blocks and flags destructive queries (DROP/DELETE/UPDATE/etc.) instead of running them blindly, and executes safe `SELECT`s live.

Backend: FastAPI + SQLite. Frontend: plain HTML/CSS/JS (no build step). Model: Claude via the Anthropic API (swap providers in `backend/llm.py` if you'd rather use OpenAI or a local model).

## Project layout

```
benchmark/
├── backend/
│   ├── main.py            # FastAPI app + routes, serves the frontend too
│   ├── knowledge_base.py  # RAG corpus + retrieval logic
│   ├── llm.py              # model provider wrapper
│   ├── db.py               # quiz stats (durable) + SQL sandbox database
│   ├── schemas.py          # request/response models
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── Dockerfile
├── Procfile
└── README.md
```

## Run it locally

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # then edit .env and add your ANTHROPIC_API_KEY

uvicorn main:app --reload
```

Open `http://localhost:8000` — the backend serves the frontend directly, so there's nothing else to run.

Get an API key at https://console.anthropic.com/settings/keys.

## Deploying

Any host that runs a Docker container or a Python web process works. Two easy options:

**Render / Railway (Docker)**
1. Push this repo to GitHub.
2. Create a new Web Service, point it at the repo — it will detect the `Dockerfile` automatically.
3. Add an environment variable `ANTHROPIC_API_KEY` with your key.
4. Deploy. The app listens on the port the platform provides.

**Railway / Heroku-style (buildpack, no Docker)**
1. Push to GitHub.
2. The `Procfile` tells the platform how to start the app (`uvicorn main:app --host 0.0.0.0 --port $PORT`).
3. Set `ANTHROPIC_API_KEY` as an environment variable.
4. Make sure the build step runs `pip install -r backend/requirements.txt`.

## Notes for an interview walkthrough

- **Retrieval is keyword/tag overlap, not embeddings.** It's simple on purpose so it's easy to explain and debug live. A natural next step — and a good thing to say if asked how you'd improve it — is hybrid retrieval (BM25 + embeddings) or a vector store like FAISS/pgvector.
- **Query Bench guards against destructive queries** with a regex check before execution — worth calling out as a deliberate safety decision, not an oversight from the original brief.
- **Quiz stats persist in SQLite** (`backend/data/stats.db`), not browser storage, so progress survives a server restart and isn't tied to one device.
- **Swapping the LLM provider** only touches `backend/llm.py` — everything else calls `llm.ask()` / `llm.ask_json()` and doesn't know which provider is behind them.

## Known limitations (worth naming proactively)

- Single shared SQL sandbox — multiple simultaneous users would share the same in-memory database. Fine for a demo; a real multi-user version would key the sandbox by session.
- No authentication — anyone who can reach the app can use it. Add an API key or login before deploying somewhere public and leaving it up.
- Quiz question quality depends entirely on the model; there's no answer-validation step checking that `correctIndex` is actually correct.
