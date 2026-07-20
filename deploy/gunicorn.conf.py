"""Shared gunicorn config enabling Prometheus multiprocess aggregation.

Every SmartHR360 Django service runs several gunicorn workers. A Prometheus
counter/gauge normally lives in the memory of *one* worker, so scraping
``/metrics`` (served by a random worker) reports only that worker's share. This
config enables prometheus_client's multiprocess mode: workers write their metric
values into ``PROMETHEUS_MULTIPROC_DIR``; django-prometheus' export view reads
*all* of them and aggregates on scrape (counters/histograms are summed, gauges
combined per their ``multiprocess_mode``).

Mounted read-only into each container and selected with
``gunicorn config.wsgi:application -c /etc/gunicorn/gunicorn.conf.py``.
Per-service tuning comes from env vars so one file fits all services.
"""

import os
import shutil

# --- Concurrency / bind (per-service via env, sane defaults) --------------
bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")
workers = int(os.environ.get("GUNICORN_WORKERS", "3"))
threads = int(os.environ.get("GUNICORN_THREADS", "1"))
worker_class = os.environ.get("GUNICORN_WORKER_CLASS", "sync")
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "30"))
accesslog = os.environ.get("GUNICORN_ACCESSLOG", "-")
errorlog = os.environ.get("GUNICORN_ERRORLOG", "-")
loglevel = os.environ.get("GUNICORN_LOGLEVEL", "info")

_MP_DIR = os.environ.get("PROMETHEUS_MULTIPROC_DIR")


def _reset_multiproc_dir():
    """Recreate an empty multiprocess dir so stale files from a previous run
    don't carry over into the aggregated values."""
    if _MP_DIR:
        shutil.rmtree(_MP_DIR, ignore_errors=True)
        os.makedirs(_MP_DIR, exist_ok=True)


def on_starting(server):
    """Master boot: start from a clean multiprocess dir."""
    _reset_multiproc_dir()


def child_exit(server, worker):
    """When a worker dies, drop its metric files so aggregation only reflects
    live processes (prevents ghost counts from restarted workers)."""
    if _MP_DIR:
        try:
            from prometheus_client import multiprocess

            multiprocess.mark_process_dead(worker.pid)
        except Exception:
            pass


# Also ensure the dir exists at config-load time (covers setups that import the
# app before on_starting fires).
if _MP_DIR:
    os.makedirs(_MP_DIR, exist_ok=True)
