#!/bin/bash
echo "Waiting for postgres to be ready..."
until docker compose exec -T postgres pg_isready -U transit_user -d transit_db; do
  echo "Postgres is unavailable - sleeping"
  sleep 5
done

echo "Postgres is up. Running migrations..."
docker compose exec -T api alembic upgrade head

echo "Running seeding scripts..."
docker compose exec -T postgres psql -U transit_user -d transit_db -c "ALTER TYPE role ADD VALUE IF NOT EXISTS 'admin';"
docker compose exec -T api python seed_users.py
docker compose exec -T api python scripts/seed_dashboard.py
echo "Seeding complete!"
