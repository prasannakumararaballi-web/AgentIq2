"""Performance benchmark suite evaluating 1,000-row and 100,000-row dataset profiling."""

import io
from pathlib import Path
import time
import numpy as np
import pandas as pd
import pytest

from agentiq_core.engine.tabular import TabularEngine
from agentiq_core.storage.local import LocalStorageService


def test_benchmark_1000_rows_demo(tmp_path: Path):
    """Benchmark profiling speed on the 1,000-row demo dataset."""
    demo_csv = Path("storage/demo/demo_customers_1000.csv")
    if not demo_csv.exists():
        pytest.skip("Demo CSV not generated yet.")

    storage = LocalStorageService(base_path=".")
    engine = TabularEngine(storage=storage)

    t0 = time.perf_counter()
    summary, findings = engine.profile_dataset("storage/demo/demo_customers_1000.csv")
    duration = time.perf_counter() - t0

    print(f"\n[Benchmark] 1,000 rows profiled in {duration:.3f}s with {len(findings)} findings.")
    # Must comfortably complete in under 2.0 seconds on stage
    assert duration < 2.0
    assert summary.total_rows == 1000
    assert len(findings) > 0


def test_benchmark_100k_rows_scale(tmp_path: Path):
    """Vectorized scale benchmark profiling 100,000 rows without memory or performance bottlenecks."""
    n_rows = 100_000
    rng = np.random.default_rng(42)

    # Generate 100k synthetic rows with vector operations
    df = pd.DataFrame({
        "id": np.arange(n_rows),
        "score": rng.normal(loc=50.0, scale=10.0, size=n_rows),
        "category": rng.choice(["Alpha", "Beta", "Gamma", "alpha", "beta"], size=n_rows),
        "status": rng.choice(["Active", "Pending", "N/A", "Unknown"], size=n_rows),
        "balance": rng.choice([0.0, 100.5, 250.0, 5000.0], size=n_rows),
        "flag": rng.choice([True, False], size=n_rows),
        "email": [f"user{i}@example.com" if i % 100 != 0 else "bad@@email" for i in range(n_rows)],
    })

    # Save to temporary storage
    storage = LocalStorageService(base_path=str(tmp_path))
    engine = TabularEngine(storage=storage)
    storage_key = "benchmark_100k.csv"
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    engine._save_bytes_to_storage(storage_key, buf.getvalue())

    t0 = time.perf_counter()
    summary, findings = engine.profile_dataset(storage_key)
    duration = time.perf_counter() - t0

    print(f"\n[Benchmark] 100,000 rows profiled in {duration:.3f}s with {len(findings)} findings.")
    # Target: 100,000 rows should profile under 10.0 seconds
    assert duration < 10.0
    assert summary.total_rows == 100_000
    assert summary.clean_rows > 0
    assert summary.dirty_rows > 0
