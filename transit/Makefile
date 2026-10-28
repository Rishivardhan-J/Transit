PY ?= ../venv/bin/python
export PYTHONPATH := .

.PHONY: data train bench seed dev test lint contrast

data:        ## build processed datasets (Amazon legs need the raw JSON in data/raw/amazon_last_mile)
	$(PY) -m src.data_processing.process_food_delivery
	$(PY) -m src.data_processing.build_amazon_legs

train:       ## train and register both model bundles
	$(PY) -m src.models.train --dataset legs
	$(PY) -m src.models.train --dataset food

bench:       ## Solomon benchmark: HGS vs OR-Tools vs Nearest Neighbour
	$(PY) -m scripts.run_benchmarks

seed:        ## local SQLite demo (no Docker, no Redis): users + one real HGS plan
	DATABASE_URL=sqlite:///./demo.db $(PY) -c "import backend.main; from backend.models_db.base import Base, engine; Base.metadata.create_all(bind=engine)"
	DATABASE_URL=sqlite:///./demo.db $(PY) seed_users.py
	DATABASE_URL=sqlite:///./demo.db $(PY) -m scripts.seed_dashboard

dev:         ## API (jobs run inline) on :8000; start the UI separately with `npm run dev` in frontend/
	DATABASE_URL=sqlite:///./demo.db CELERY_EAGER=true ../venv/bin/uvicorn backend.main:app --reload --port 8000

test:
	$(PY) -m pytest -q -m "not slow"
	cd frontend && npm test

lint:
	../venv/bin/ruff check src backend scripts tests --select E9,F63,F7,F82
	cd frontend && npm run lint

contrast:
	$(PY) -m scripts.contrast_check
