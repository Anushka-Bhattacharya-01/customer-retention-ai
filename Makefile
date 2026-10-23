.PHONY: install data train test serve up down ask

install:
	pip install -r requirements.txt

data:
	python data/generate_data.py

train:
	python -m src.train

test:
	python -m pytest -v

serve:
	uvicorn src.app:app --reload --port 8000

up:
	docker compose up --build -d

down:
	docker compose down

ask:
	curl -s -X POST localhost:8000/assistant/ask -H "Content-Type: application/json" \
	  -d '{"question":"Will customer C0014 leave? What should we offer?"}' | python -m json.tool
