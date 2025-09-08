.PHONY: up down build sh migrate superuser scrape test

up:
\tdocker compose up -d

down:
\tdocker compose down -v

build:
\tdocker compose build

sh:
\tdocker compose exec web bash

migrate:
\tdocker compose exec web python manage.py migrate

superuser:
\tdocker compose exec web python manage.py createsuperuser

scrape:
\tdocker compose exec web python manage.py scrape --source indeed --q "Data Analyst" --loc "Lagos" --pages 1

test:
\tdocker compose exec web pytest -q
