from celery import Celery

from .config import get_settings


settings = get_settings()

celery_app = Celery(
    "edupulse",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    # ── Serialization ──
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # ── Task Behaviour ──
    task_acks_late=True,                    # Ack after execution (crash-safe)
    task_reject_on_worker_lost=True,        # Re-queue if worker dies
    task_track_started=True,                # Track STARTED state
    result_expires=3600,                    # Results expire after 1 hour

    # ── Time Limits ──
    task_soft_time_limit=120,               # Soft limit: 2 minutes
    task_time_limit=180,                    # Hard limit: 3 minutes

    # ── Concurrency ──
    worker_concurrency=settings.celery_concurrency,
    worker_prefetch_multiplier=1,           # Fair scheduling

    # ── Broker Connection ──
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,

    # ── Task Routing ──
    task_routes={
        "app.tasks.send_notification": {"queue": "notifications"},
    },
    task_default_queue="default",

    # ── Error Handling ──
    task_annotations={
        "app.tasks.send_notification": {
            "max_retries": 3,
            "default_retry_delay": 10,
        },
    },
)

