"""
Serialized background job queue for the inference API.

Inference is the expensive part of the pipeline: loading two FastAI models and running
them over a tile pair takes minutes, so it cannot happen inside a request. Jobs are
submitted here, executed one at a time on a worker thread (never in parallel, otherwise
two jobs fight over the same GPU), and polled through their id.

This module deliberately depends only on the standard library: the FastAPI layer injects
the callable that actually does the work, which keeps the queue testable on its own.
"""

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

LOG = logging.getLogger("jobs")

MAX_RETAINED_JOBS = 200


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class JobQueueFull(RuntimeError):
    """Raised when too many jobs are already waiting; the caller should return 429."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Job:
    id: str
    zone_id: str
    status: JobStatus = JobStatus.QUEUED
    created_at: str = field(default_factory=utc_now)
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    tiles: int = 0
    affected: int = 0
    unaffected: int = 0
    severe: int = 0
    moderate: int = 0
    artifacts: List[str] = field(default_factory=list)
    error: Optional[str] = None
    # Non-fatal problem worth surfacing, e.g. artifacts written but GeoServ not reloaded.
    warning: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.id,
            "zone_id": self.zone_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_seconds": self.duration_seconds,
            "tiles": self.tiles,
            "affected_structures": self.affected,
            "unaffected_structures": self.unaffected,
            "severe_structures": self.severe,
            "moderate_structures": self.moderate,
            "artifacts": self.artifacts,
            "error": self.error,
            "warning": self.warning,
        }


# A worker receives the job and fills in whatever it knows; any exception marks it failed.
Worker = Callable[[Job], None]


class JobQueue:
    """Runs submitted workers one at a time on daemon threads."""

    def __init__(self, max_pending: int = 4, max_retained: int = MAX_RETAINED_JOBS):
        self._lock = threading.Lock()
        self._worker_slot = threading.Semaphore(1)
        self._jobs: Dict[str, Job] = {}
        self._max_pending = max_pending
        self._max_retained = max_retained

    @property
    def max_pending(self) -> int:
        return self._max_pending

    def submit(self, zone_id: str, worker: Worker) -> Job:
        with self._lock:
            waiting = sum(
                1 for job in self._jobs.values()
                if job.status in (JobStatus.QUEUED, JobStatus.RUNNING)
            )
            if waiting >= self._max_pending:
                raise JobQueueFull(
                    f"{waiting} inference job(s) already waiting "
                    f"(limit {self._max_pending}); retry when one finishes"
                )

            job = Job(id=str(uuid.uuid4()), zone_id=zone_id)
            self._jobs[job.id] = job
            self._prune()

        thread = threading.Thread(
            target=self._execute,
            args=(job, worker),
            name=f"inference-{job.id[:8]}",
            daemon=True,
        )
        thread.start()
        return job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self, limit: int = 20) -> List[Job]:
        with self._lock:
            jobs = list(self._jobs.values())
        jobs.reverse()  # newest first, dicts keep insertion order
        return jobs[:limit]

    def active_count(self) -> int:
        with self._lock:
            return sum(
                1 for job in self._jobs.values()
                if job.status in (JobStatus.QUEUED, JobStatus.RUNNING)
            )

    def _execute(self, job: Job, worker: Worker) -> None:
        with self._worker_slot:
            started = time.monotonic()
            with self._lock:
                job.status = JobStatus.RUNNING
                job.started_at = utc_now()

            LOG.info("job %s started for zone %s", job.id, job.zone_id)
            try:
                worker(job)
            except Exception as error:  # noqa: BLE001 - the reason is reported to the caller
                LOG.exception("job %s failed", job.id)
                with self._lock:
                    job.status = JobStatus.FAILED
                    job.error = f"{type(error).__name__}: {error}"
            else:
                with self._lock:
                    job.status = JobStatus.SUCCEEDED
                LOG.info("job %s finished for zone %s", job.id, job.zone_id)
            finally:
                with self._lock:
                    job.finished_at = utc_now()
                    job.duration_seconds = round(time.monotonic() - started, 3)

    def _prune(self) -> None:
        """Drops the oldest finished jobs once the history grows past the cap."""
        if len(self._jobs) <= self._max_retained:
            return

        finished = [
            job_id for job_id, job in self._jobs.items()
            if job.status in (JobStatus.SUCCEEDED, JobStatus.FAILED)
        ]
        for job_id in finished[: len(self._jobs) - self._max_retained]:
            self._jobs.pop(job_id, None)
