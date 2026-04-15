"""Run the full benchmark suite: each configuration 5 times."""

from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    MofNCompleteColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from benchmark import run_benchmark, save_result, console

REPEATS = 5

CASES = [
    {"factor": 2, "max_depth": 0, "sleep": 0.5, "n": 1023},
    {"factor": 2, "max_depth": 1, "sleep": 0.5, "n": 1023},
    {"factor": 2, "max_depth": 2, "sleep": 0.5, "n": 1023},
    {"factor": 2, "max_depth": 3, "sleep": 0.5, "n": 1023},
    {"factor": 2, "max_depth": 4, "sleep": 0.5, "n": 1023},
    {"factor": 2, "max_depth": 5, "sleep": 0.5, "n": 1023},
    {"factor": 2, "max_depth": 6, "sleep": 0.5, "n": 1023},
    {"factor": 4, "max_depth": 1, "sleep": 0.5, "n": 1023},
    {"factor": 4, "max_depth": 2, "sleep": 0.5, "n": 1023},
    {"factor": 4, "max_depth": 3, "sleep": 0.5, "n": 1023},
    {"factor": 8, "max_depth": 1, "sleep": 0.5, "n": 1023},
    {"factor": 8, "max_depth": 2, "sleep": 0.5, "n": 1023},
    {"factor": 16, "max_depth": 1, "sleep": 0.5, "n": 1023},
    {"factor": 32, "max_depth": 1, "sleep": 0.5, "n": 1023},
    {"factor": 64, "max_depth": 1, "sleep": 0.5, "n": 1023},
]

total = len(CASES) * REPEATS
succeeded = 0
failed = 0


def main():
    global succeeded, failed

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    )

    with progress:
        suite_task = progress.add_task("Suite", total=total)
        run_num = 0

        for case_idx, case in enumerate(CASES):
            case_label = f"f{case['factor']}-d{case['max_depth']}"
            case_task = progress.add_task(f"  {case_label}", total=REPEATS)

            for rep in range(1, REPEATS + 1):
                run_num += 1
                label = (
                    f"f{case['factor']}-d{case['max_depth']}-s{case['sleep']}-r{rep}"
                )
                progress.update(
                    suite_task, description=f"Suite [{run_num}/{total}] {label}"
                )

                try:
                    row = run_benchmark(
                        n=case["n"],
                        factor=case["factor"],
                        max_depth=case["max_depth"],
                        sleep_duration=case["sleep"],
                        run_name=label,
                    )
                    save_result(row)
                    succeeded += 1
                    progress.log(
                        f"[green]OK[/green] {label} — "
                        f"total={row['t_total_s']}s "
                        f"(alloc={row['t_allocate_s']}s, exec={row['t_execute_s']}s)"
                    )
                except Exception as e:
                    failed += 1
                    progress.log(f"[bold red]FAIL[/bold red] {label} — {e}")

                progress.advance(case_task)
                progress.advance(suite_task)

            progress.update(case_task, visible=False)

    console.print()
    console.rule("Suite Complete")
    console.print(
        f"  [green]{succeeded} succeeded[/green]"
        f"  [red]{failed} failed[/red]"
        f"  [dim]({total} total)[/dim]"
    )


if __name__ == "__main__":
    main()
