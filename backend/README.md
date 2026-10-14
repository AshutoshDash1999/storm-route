# Backend (Django)

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then set SECRET_KEY
python manage.py migrate
```

## Run

```bash
python manage.py runserver   # http://127.0.0.1:8000
```

Health check: `GET /api/health/` → `{"status": "ok"}`

CORS allows the Vite dev server at `http://localhost:5173`.
