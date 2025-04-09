.PHONY: up down recreate-db run-local create-admin

up:
	docker-compose up --build

down:
	docker-compose down

recreate-db:
	docker-compose exec app python -m scripts.recreate_db

run-local:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

create-admin:
	docker-compose exec app python -m scripts.create_admin