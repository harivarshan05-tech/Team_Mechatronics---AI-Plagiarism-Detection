"""
Benchmark API Router:
Executes high-throughput 300 submissions benchmark on-demand.
"""

from fastapi import APIRouter
from app.models import BenchmarkResult
from benchmark_300 import run_benchmark

router = APIRouter(prefix="/api/benchmark", tags=["Benchmark"])


@router.post("/run")
def trigger_benchmark():
    res = run_benchmark()
    return res
