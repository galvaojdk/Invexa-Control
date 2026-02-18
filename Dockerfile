FROM python:3.11-slim




# Install system dependencies (pg_dump)
# Add PGDG repo to get latest postgresql-client (matching server v18)
# Using curl + gpg --dearmor which is more robust on slim images than apt-key
RUN apt-get update && apt-get install -y lsb-release curl ca-certificates gnupg2 && \
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /etc/apt/trusted.gpg.d/postgresql.gpg && \
    sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list' && \
    apt-get update && apt-get install -y postgresql-client && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["/bin/bash", "-c", "bash migrate.sh && uvicorn app.main:app --host 0.0.0.0 --port 10000"]
