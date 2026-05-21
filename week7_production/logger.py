"""
week7_production/logger.py
===========================
Structured AI request/response logger.
Logs every LLM call with timing, cost estimate, and metadata.
In production: ship logs to Datadog / Grafana / CloudWatch.
"""

import json
import time
import datetime
import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Optional
from pathlib import Path


# ── Log record ─────────────────────────────────────────────────────────────

@dataclass
class AICallLog:
    timestamp: str
    model: str
    prompt_preview: str          # first 200 chars of prompt
    response_preview: str        # first 200 chars of response
    latency_ms: float
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    total_tokens: Optional[int]
    estimated_cost_usd: Optional[float]
    success: bool
    error: Optional[str] = None
    extra: dict = field(default_factory=dict)


# ── Cost estimates (per 1M tokens, rough 2025 prices) ─────────────────────

COST_MAP = {
    "groq:llama-3.1-8b-instant":    {"input": 0.05,  "output": 0.08},
    "groq:llama-3.1-70b-versatile": {"input": 0.59,  "output": 0.79},
    "groq:llama-3.3-70b-versatile": {"input": 0.59,  "output": 0.79},
    "openai/gpt-4o":                {"input": 5.0,   "output": 15.0},
    "anthropic/claude-3-5-sonnet":  {"input": 3.0,   "output": 15.0},
}


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Rough cost estimate in USD."""
    prices = COST_MAP.get(model, {"input": 1.0, "output": 2.0})  # fallback
    return (
        prompt_tokens     / 1_000_000 * prices["input"] +
        completion_tokens / 1_000_000 * prices["output"]
    )


# ── Logger ─────────────────────────────────────────────────────────────────

class AILogger:
    """Structured logger for all AI agent calls."""

    def __init__(self, log_file: str = "ai_calls.jsonl", console: bool = True):
        self.log_file = Path(log_file)
        self.console = console
        self._session_calls: list[AICallLog] = []

        # Python stdlib logger for console output
        self._logger = logging.getLogger("ai_logger")
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
            self._logger.addHandler(handler)
        self._logger.setLevel(logging.INFO)

    def log(
        self,
        model: str,
        prompt: str,
        response: Any,
        latency_ms: float,
        usage: Optional[dict] = None,
        error: Optional[str] = None,
        **extra,
    ) -> AICallLog:
        prompt_tokens     = (usage or {}).get("prompt_tokens", 0)
        completion_tokens = (usage or {}).get("completion_tokens", 0)
        total_tokens      = (usage or {}).get("total_tokens", prompt_tokens + completion_tokens)

        cost = estimate_cost(model, prompt_tokens, completion_tokens) if usage else None

        record = AICallLog(
            timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
            model=model,
            prompt_preview=str(prompt)[:200],
            response_preview=str(response)[:200],
            latency_ms=round(latency_ms, 2),
            prompt_tokens=prompt_tokens or None,
            completion_tokens=completion_tokens or None,
            total_tokens=total_tokens or None,
            estimated_cost_usd=round(cost, 8) if cost else None,
            success=error is None,
            error=error,
            extra=extra,
        )

        self._session_calls.append(record)

        # Write to JSONL file
        with self.log_file.open("a") as f:
            f.write(json.dumps(asdict(record)) + "\n")

        # Console output
        if self.console:
            status = "OK" if record.success else "FAIL"
            self._logger.info(
                f"[{status}] {model} | {latency_ms:.0f}ms | "
                f"~${cost:.6f}" if cost else f"[{status}] {model} | {latency_ms:.0f}ms"
            )

        return record

    def session_stats(self) -> dict:
        """Aggregate stats for the current session."""
        if not self._session_calls:
            return {"calls": 0}
        total_cost = sum(r.estimated_cost_usd or 0 for r in self._session_calls)
        total_latency = sum(r.latency_ms for r in self._session_calls)
        successes = sum(1 for r in self._session_calls if r.success)
        return {
            "calls": len(self._session_calls),
            "successes": successes,
            "failures": len(self._session_calls) - successes,
            "total_latency_ms": round(total_latency, 2),
            "avg_latency_ms": round(total_latency / len(self._session_calls), 2),
            "total_cost_usd": round(total_cost, 6),
        }


# ── Rate limiter ───────────────────────────────────────────────────────────

class RateLimiter:
    """
    Simple token-bucket rate limiter.
    Prevents hammering the API when looping.

    Usage:
        limiter = RateLimiter(requests_per_minute=30)
        await limiter.acquire()
        result = await agent.run(...)
    """

    def __init__(self, requests_per_minute: int = 30):
        self.rpm = requests_per_minute
        self._min_interval = 60.0 / requests_per_minute
        self._last_call: float = 0.0

    async def acquire(self) -> None:
        import asyncio
        elapsed = time.monotonic() - self._last_call
        wait = self._min_interval - elapsed
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_call = time.monotonic()

    def acquire_sync(self) -> None:
        elapsed = time.monotonic() - self._last_call
        wait = self._min_interval - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()
