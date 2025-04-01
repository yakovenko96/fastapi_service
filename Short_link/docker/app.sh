#!/bin/bash
sleep 10
alembic revision --autogenerate -m "Initial migrations"
alembic upgrade head

gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind=0.0.0.0:8000