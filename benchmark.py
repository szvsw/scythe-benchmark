"""Benchmark runner for Scythe scatter/gather subdivision strategies.

Measures wall-clock time to completion for N tasks under different
scatter/gather tree configurations (factor, max_depth).

Usage:
    python benchmark.py --n 65536 --factor 256 --max-depth 1 --sleep 0.5
    python benchmark.py --n 65536 --factor 16 --max-depth 2 --sleep 0
    python benchmark.py --n 65536 --factor 2 --max-depth 8 --run-name binary-tree
"""

import argparse
import csv
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from scythe.experiments import BaseExperiment
from scythe.scatter_gather import RecursionMap

from experiments.sleep_experiment import SleepInput, sleep_task

console = Console()
RESULTS_DIR = Path("results")
RESULTS_CSV = RESULTS_DIR / "benchmark.csv"


def generate_specs(n: int, sleep_duration: float) -> list[SleepInput]:
    df = pd.DataFrame(
        {
            "sleep_duration": [sleep_duration] * n,
            "experiment_id": ["placeholder"] * n,
            "sort_index": range(n),
        }
    )
    return [SleepInput.model_validate(row.to_dict()) for _, row in df.iterrows()]


def run_benchmark(
    n: int,
    factor: int,
    max_depth: int,
    sleep_duration: float,
    run_name: str,
) -> dict:
    console.print(
        f"[bold]Benchmark:[/bold] n={n}, factor={factor}, max_depth={max_depth}, "
        f"sleep={sleep_duration}s, run_name={run_name}"
    )

    specs = generate_specs(n, sleep_duration)
    experiment = BaseExperiment(runnable=sleep_task, run_name=run_name)
    recursion_map = RecursionMap(factor=factor, max_depth=max_depth)

    console.print(f"Allocating {n} specs...")
    t_start = time.monotonic()

    run, ref = experiment.allocate(
        specs,
        version="bumpmajor",
        recursion_map=recursion_map,
    )

    t_allocated = time.monotonic()
    t_allocate_s = t_allocated - t_start
    console.print(
        f"Allocated in [bold cyan]{t_allocate_s:.2f}s[/bold cyan] "
        f"(workflow_run_id={ref.workflow_run_id})"
    )

    console.print("Waiting for completion...")
    ref.result()
    t_done = time.monotonic()

    t_execute_s = t_done - t_allocated
    t_total_s = t_done - t_start

    return {
        "run_name": run_name,
        "n": n,
        "factor": factor,
        "max_depth": max_depth,
        "sleep": sleep_duration,
        "t_allocate_s": round(t_allocate_s, 3),
        "t_execute_s": round(t_execute_s, 3),
        "t_total_s": round(t_total_s, 3),
        "workflow_run_id": ref.workflow_run_id,
        "experiment_id": run.experiment_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def save_result(row: dict) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    file_exists = RESULTS_CSV.exists()
    with open(RESULTS_CSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def print_summary(row: dict) -> None:
    table = Table(title="Benchmark Result")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    display = {
        "Run name": row["run_name"],
        "N tasks": str(row["n"]),
        "Factor": str(row["factor"]),
        "Max depth": str(row["max_depth"]),
        "Sleep (s)": str(row["sleep"]),
        "Allocation time (s)": str(row["t_allocate_s"]),
        "Execution time (s)": str(row["t_execute_s"]),
        "Total time (s)": str(row["t_total_s"]),
        "Workflow run ID": row["workflow_run_id"],
        "Experiment ID": row["experiment_id"],
    }
    for k, v in display.items():
        table.add_row(k, v)
    console.print(Panel(table, border_style="green"))


def main():
    parser = argparse.ArgumentParser(description="Scythe subdivision benchmark")
    parser.add_argument("--n", type=int, default=65536, help="Number of leaf tasks")
    parser.add_argument(
        "--factor", type=int, required=True, help="Scatter/gather branching factor"
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        required=True,
        help="Maximum recursion depth (0 = no subdivision)",
    )
    parser.add_argument(
        "--sleep", type=float, default=0.0, help="Sleep duration per task (seconds)"
    )
    parser.add_argument(
        "--run-name",
        type=str,
        default=None,
        help="Label for this run (default: auto-generated)",
    )
    args = parser.parse_args()

    if args.run_name is None:
        args.run_name = f"bench-f{args.factor:02d}-d{args.max_depth:01d}-s{args.sleep:.1f}-n{args.n:06d}"

    row = run_benchmark(
        n=args.n,
        factor=args.factor,
        max_depth=args.max_depth,
        sleep_duration=args.sleep,
        run_name=args.run_name,
    )
    save_result(row)
    print_summary(row)
    console.print(f"Results appended to [bold]{RESULTS_CSV}[/bold]")


if __name__ == "__main__":
    main()
