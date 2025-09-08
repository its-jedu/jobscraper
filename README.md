# Job Scraper Dashboard

Django + Postgres + Redis + Celery + Selenium. Scrapes jobs (Indeed MVP), stores with dedup, exposes REST API + HTML dashboard.

## Quickstart
1) `cp .env.example .env` (edit as needed)
2) `docker compose build && docker compose up -d`
3) `docker compose exec web python manage.py migrate`
4) `docker compose exec web python manage.py createsuperuser`
5) Trigger a scrape: `make scrape`
6) Open:
   - Dashboard: http://localhost:8000/
   - API list: http://localhost:8000/api/jobs/
   - Swagger:  http://localhost:8000/api/schema/swagger-ui/

## Notes
- Celery Beat can schedule recurring scrapes.
- `jobs.Job.hash_key` enforces dedup.
- See `scraper/selectors/indeed.py` for Selenium logic.
