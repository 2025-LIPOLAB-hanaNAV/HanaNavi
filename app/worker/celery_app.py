import os
from celery import Celery


def _redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://redis:6379/0")


app = Celery("worker", broker=_redis_url(), backend=_redis_url())
app.conf.task_routes = {"app.worker.tasks.*": {"queue": "default"}}
app.conf.task_default_queue = "default"

