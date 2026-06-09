# Local Development

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install ".[dev]"
python -m app.scripts.migrate
python -m app.scripts.seed
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Docker:

```bash
docker compose up --build
```

Troubleshooting:

- If login fails, rerun `make seed`.
- If frontend cannot reach backend, verify `NEXT_PUBLIC_API_BASE_URL`.
- Keep tests on mock provider so no OpenAI calls are made.

