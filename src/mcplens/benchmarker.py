from __future__ import annotations

import json
import statistics
import time
from typing import Any, Dict, Optional

from mcplens.client import MCPClient
from mcplens.models import BenchmarkResult


async def run_benchmark(
    command: str,
    tool_name: Optional[str] = None,
    tool_args: Optional[Dict[str, Any]] = None,
    iterations: int = 20,
    timeout: float = 15.0,
) -> BenchmarkResult:
    latencies: list[float] = []
    successful = 0
    failed = 0
    total_bytes = 0

    async with MCPClient(command=command, timeout=timeout) as client:
        await client.initialize()

        t_start = time.perf_counter()
        for _ in range(iterations):
            t0 = time.perf_counter()
            try:
                if tool_name:
                    res, _ = await client.call_tool(tool_name, tool_args or {})
                    total_bytes += len(json.dumps(res))
                else:
                    await client.ping()
                    total_bytes += 30
                latencies.append((time.perf_counter() - t0) * 1000.0)
                successful += 1
            except Exception:
                latencies.append((time.perf_counter() - t0) * 1000.0)
                failed += 1

        total_duration = time.perf_counter() - t_start

    if not latencies:
        raise RuntimeError("No benchmark iterations completed")

    latencies.sort()
    n = len(latencies)
    min_lat = round(latencies[0], 2)
    max_lat = round(latencies[-1], 2)
    mean_lat = round(statistics.mean(latencies), 2)
    median_lat = round(statistics.median(latencies), 2)
    p95_lat = round(latencies[int(0.95 * n)] if n > 1 else latencies[0], 2)
    p99_lat = round(latencies[int(0.99 * n)] if n > 1 else latencies[0], 2)
    rps = round(iterations / total_duration, 2) if total_duration > 0 else 0.0

    return BenchmarkResult(
        iterations=iterations,
        successful_calls=successful,
        failed_calls=failed,
        min_latency_ms=min_lat,
        mean_latency_ms=mean_lat,
        median_latency_ms=median_lat,
        p95_latency_ms=p95_lat,
        p99_latency_ms=p99_lat,
        max_latency_ms=max_lat,
        requests_per_second=rps,
        total_payload_bytes=total_bytes,
    )
