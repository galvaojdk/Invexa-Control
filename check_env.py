from app.core.config import settings
from app.core.database import engine

print(f"Settings DATABASE_URL: {settings.DATABASE_URL}")
print(f"Engine URL: {engine.url}")
print(f"Engine Dialect: {engine.dialect.name}")
