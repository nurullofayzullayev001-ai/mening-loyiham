"""Aytilgan vaqtda vazifani bajarish (eslatma / rejalashtirish)."""

from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from typing import Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    TZ = ZoneInfo("Asia/Tashkent")
except ZoneInfoNotFoundError:  # telefonda vaqt mintaqalari bazasi bo'lmasa
    TZ = timezone(timedelta(hours=5), "UZT")  # Toshkent: UTC+5, yozgi vaqt yo'q


class Scheduler:
    def __init__(self) -> None:
        self.runner: Callable[[str], None] | None = None  # __main__ o'rnatadi
        self._jobs: dict[int, tuple[datetime, str, threading.Timer]] = {}
        self._next_id = 1
        self._lock = threading.Lock()

    def add(self, when: str, task: str) -> str:
        at = parse_time(when)
        delay = (at - datetime.now(TZ)).total_seconds()
        with self._lock:
            job_id = self._next_id
            self._next_id += 1
            timer = threading.Timer(delay, self._fire, args=(job_id,))
            timer.daemon = True
            self._jobs[job_id] = (at, task, timer)
        timer.start()
        return f"#{job_id} rejalashtirildi: {at:%Y-%m-%d %H:%M} da - {task}"

    def _fire(self, job_id: int) -> None:
        with self._lock:
            job = self._jobs.pop(job_id, None)
        if job and self.runner:
            self.runner(job[1])

    def list(self) -> str:
        with self._lock:
            jobs = sorted(self._jobs.items(), key=lambda kv: kv[1][0])
        if not jobs:
            return "Rejalashtirilgan vazifalar yo'q."
        return "\n".join(f"#{i}: {at:%Y-%m-%d %H:%M} - {task}" for i, (at, task, _) in jobs)

    def cancel(self, job_id: int) -> str:
        with self._lock:
            job = self._jobs.pop(job_id, None)
        if not job:
            return f"#{job_id} topilmadi."
        job[2].cancel()
        return f"#{job_id} bekor qilindi."


def parse_time(when: str) -> datetime:
    """'15:30', '2026-11-10 15:30' yoki '+20' (20 daqiqadan keyin)."""
    now = datetime.now(TZ)
    when = when.strip()
    try:
        if when.startswith("+"):
            minutes = float(when[1:])
            if not 0 < minutes <= 7 * 24 * 60:
                raise ValueError
            return now + timedelta(minutes=minutes)
        if len(when) <= 5:
            t = datetime.strptime(when, "%H:%M").time()
            at = datetime.combine(now.date(), t, TZ)
            return at if at > now else at + timedelta(days=1)
        at = datetime.strptime(when, "%Y-%m-%d %H:%M").replace(tzinfo=TZ)
    except ValueError as exc:
        raise ValueError("Vaqt formati: 'HH:MM', 'YYYY-MM-DD HH:MM' yoki '+daqiqa'.") from exc
    if at <= now:
        raise ValueError("Bu vaqt allaqachon o'tib ketgan.")
    return at


SCHEDULER = Scheduler()
