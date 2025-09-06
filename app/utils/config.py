import os
from typing import Dict


def get_settings() -> Dict[str, str]:
    return {
        "QDRANT_URL": os.getenv("QDRANT_URL", "http://qdrant:6333"),
        "REDIS_URL": os.getenv("REDIS_URL", "redis://redis:6379/0"),
        "POSTGRES_DSN": os.getenv(
            "POSTGRES_DSN", "postgresql://postgres:postgres@postgres:5432/dify"
        ),
        "OLLAMA_BASE_URL": os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
        "STORAGE_DIR": os.getenv("STORAGE_DIR", "/data/storage"),
        "SQLITE_PATH": os.getenv("SQLITE_PATH", "/data/sqlite/ir.db"),
    }

