# Benchmark — measure what you actually know

A small full-stack app with three modules:

- **Learn** — retrieval-augmented Q&A over a curated DSA notes library (keyword/tag-overlap retrieval)
- **Calibrate** — generates a 5-question multiple-choice quiz per topic on demand, with instant feedback and a persistent calibration report (accuracy by topic).
- **Query Bench** — turns a plain-English question into SQL against a real SQLite database, blocks and flags destructive queries (DROP/DELETE/UPDATE/etc.) instead of running them blindly, and executes safe `SELECT`s live.

Backend: FastAPI + SQLite. Frontend: plain HTML/CSS/JS (no build step). Model: Gemini via the Gemini API (swap providers in `backend/llm.py` if you'd rather use OpenAI or a local model).

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

cp .env.example .env            # then edit .env and add your GEMINI_API_KEY

uvicorn main:app --reload
```

Open `http://localhost:8000` — the backend serves the frontend directly, so there's nothing else to run.

Get an API key at https://console.anthropic.com/settings/keys.

## Deploying

Any host that runs a Docker container or a Python web process works. Two easy options:

**Render / Railway (Docker)**
1. Push this repo to GitHub.
2. Create a new Web Service, point it at the repo — it will detect the `Dockerfile` automatically.
3. Add an environment variable `GEMINI_API_KEY` with your key.
4. Deploy. The app listens on the port the platform provides.

**Railway / Heroku-style (buildpack, no Docker)**
1. Push to GitHub.
2. The `Procfile` tells the platform how to start the app (`uvicorn main:app --host 0.0.0.0 --port $PORT`).
3. Set `GEMINI_API_KEY` as an environment variable.
4. Make sure the build step runs `pip install -r backend/requirements.txt`.
