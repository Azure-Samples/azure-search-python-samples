"""Function-only 429 recovery; all records share one request deadline.

EMBED_DOCUMENT_RETRY_BUDGET_SECONDS defaults to 120 (allowed 1..120).
EMBED_QUERY_RETRY_BUDGET_SECONDS defaults to 20 (allowed 1..20).
EMBED_MAX_429_ATTEMPTS defaults to 4, including the first call (allowed 1..4).
Retry-After is honored, never shortened to fit. Provider connect/read timeouts
are bounded by remaining budget, with reads capped at 60 seconds. Socket read
timeouts are inactivity limits, not a hard kill of a continuously streaming peer.
"""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import math
import os
import time

from embedding_engine import TransientProviderError


class RetryingEmbeddingEngine:
    def __init__(self, engine, role, clock=None, sleep=None):
        self.engine = engine
        self.clock = clock or time.monotonic
        self.sleep = sleep or time.sleep
        limit = 120 if role == "document" else 20
        try:
            budget = float(os.environ.get(
                f"EMBED_{role.upper()}_RETRY_BUDGET_SECONDS", str(limit)))
            self.attempts = int(os.environ.get("EMBED_MAX_429_ATTEMPTS", "4"))
        except ValueError as exc:
            raise RuntimeError("Invalid Function retry configuration") from exc
        if not math.isfinite(budget) or not 1 <= budget <= limit or not 1 <= self.attempts <= 4:
            raise RuntimeError("Function retry budget/attempt limit is outside the allowed bounds")
        self.deadline = self.clock() + budget

    @staticmethod
    def retry_delay(retry_after, attempt):
        fallback = 2 ** attempt
        if retry_after is None:
            return fallback
        try:
            delay = float(retry_after)
        except (ValueError, TypeError):
            try:
                delay = (parsedate_to_datetime(retry_after) -
                         datetime.now(timezone.utc)).total_seconds()
            except (ValueError, TypeError, OverflowError):
                return fallback
        return max(delay, 0) if math.isfinite(delay) else fallback

    def embed(self, model, role, text, dimensions=None):
        for attempt in range(self.attempts):
            remaining = self.deadline - self.clock()
            if remaining <= 0.05:
                raise TransientProviderError(429, "1")
            connect = min(10, remaining / 2)
            timeout = (connect, min(60, remaining - connect))
            try:
                return self.engine.embed(model, role, text, dimensions, timeout=timeout)
            except TransientProviderError as exc:
                if exc.status != 429 or attempt + 1 == self.attempts:
                    raise
                delay = self.retry_delay(exc.retry_after, attempt)
                if delay + 0.05 >= self.deadline - self.clock():
                    raise
                self.sleep(delay)
