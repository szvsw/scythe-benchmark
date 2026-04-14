# Scythe Subdivision Benchmark

Benchmark suite measuring how scatter/gather tree subdivision depth and branching factor affect total wall-clock time to solution in [Scythe](https://github.com/szvsw/scythe).

This addresses the question: does recursively subdividing a large pool of tasks into a tree of scatter/gather nodes improve throughput compared to dispatching all tasks from a single node?

## Benchmark Design

All cases dispatch **N = 1023** leaf tasks with a 0.5s sleep per task. The suite varies `factor` (branching factor) and `max_depth` (recursion depth) across 14 configurations, each repeated 5 times (70 total runs):

| `--factor` | `--max-depth` | Terminal nodes |
|------------|---------------|----------------|
| 0          | 0             | 1 (no subdivision) |
| 2          | 1             | 2              |
| 4          | 1             | 4              |
| 8          | 1             | 8              |
| 16         | 1             | 16             |
| 32         | 1             | 32             |
| 2          | 2             | 4              |
| 4          | 2             | 16             |
| 8          | 2             | 64             |
| 2          | 3             | 8              |
| 4          | 3             | 64             |
| 2          | 4             | 16             |
| 2          | 5             | 32             |
| 2          | 6             | 64             |

This explores the two-dimensional parameter space (factor x depth) and allows comparing configurations that produce the same number of terminal nodes via different tree shapes.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (with Docker Compose v2)
- [uv](https://astral.sh/uv) package manager
- A [Hatchet Cloud](https://cloud.hatchet.run) account with an API token
- An S3 bucket with AWS credentials

## Setup

### 1. Install dependencies

```sh
make install
```

### 2. Configure environment

```sh
cp .env.example .env
```

Edit `.env` with your Hatchet Cloud token, AWS credentials, and S3 bucket name.

### 3. Start workers

```sh
make up
```

This starts fanout workers (scatter/gather orchestration) and simulation workers (leaf tasks). Adjust `SIMULATIONS_REPLICAS` to scale:

```sh
SIMULATIONS_REPLICAS=32 docker compose up -d --build
```

## Running the Full Suite

The recommended way to run all benchmark configurations:

```sh
make suite
```

This runs all 14 configurations x 5 repeats = 70 benchmark runs sequentially, with a Rich progress display showing overall completion, elapsed time, and estimated time remaining. Results are appended to `results/benchmark.csv`.

## Running Individual Benchmarks

For one-off runs or custom configurations:

```sh
make bench ARGS="--factor 16 --max-depth 1 --sleep 0.5 --n 1023"
make bench ARGS="--factor 2 --max-depth 0 --sleep 0 --n 4096 --run-name custom-flat"
```

## Plotting Results

The `plots.ipynb` Jupyter notebook produces publication-quality figures from `results/benchmark.csv`. It generates five plots:

1. **Terminal Nodes vs Total Time** -- Scatter with error bars, color = max_depth
2. **Terminal Nodes vs Total Time (dodged)** -- Same data with configurations sharing a terminal-node count spread apart horizontally for clarity; color = depth, marker = factor
3. **Factor vs Total Time by Depth** -- Line plot with error bands per recursion depth
4. **Factor x Depth Heatmap** -- Bubble chart with color encoding mean runtime and size encoding terminal nodes
5. **Ranked Configurations** -- Horizontal bar chart sorted by speed, with speedup annotations relative to the no-subdivision baseline
6. **Speedup vs Terminal Nodes** -- Speedup factor plotted against terminal nodes

All figures are saved as PDF and PNG to `results/figures/`.

To run the notebook:

```sh
uv run jupyter notebook plots.ipynb
```

## Results Format

### `results/benchmark.csv`

| Column | Description |
|--------|-------------|
| run_name | Label for this run |
| n | Number of leaf tasks |
| factor | Scatter/gather branching factor |
| max_depth | Maximum recursion depth |
| sleep | Sleep duration per task (seconds) |
| t_allocate_s | Time to allocate (upload specs, trigger workflow) |
| t_execute_s | Time from allocation to completion |
| t_total_s | Total wall-clock time |
| workflow_run_id | Hatchet workflow run ID |
| experiment_id | Scythe experiment ID |
| timestamp | ISO timestamp |

## Stopping

```sh
make down
```

## AWS Deployment

For running benchmarks at scale on AWS ECS with spot capacity, an [SST](https://sst.dev) infrastructure-as-code configuration is provided in `infra/`.

### Setup

```sh
cd infra
cp .env.example .env
```

Edit `infra/.env` with your AWS account ID, region, Hatchet token, S3 bucket, and desired replica counts (`SIM_COUNT`, `FAN_COUNT`).

### Push worker image to ECR (recommended)

Pre-building and pushing the worker image to ECR significantly speeds up deploys (SST doesn't need to build the Docker image each time). You only need to re-push when experiment code changes.

First, create the ECR repository (one-time):

```sh
aws ecr create-repository --repository-name scythe-benchmark/worker --region us-east-1
```

Then build and push:

```sh
make push-worker
```

Set `USE_PREBUILT_IMAGE=true` in `infra/.env` (the default in the example) to use the pushed image.

### Deploy

```sh
cd infra
npx sst deploy --stage benchmark
```

This provisions a VPC, ECS cluster, and two Fargate spot services (simulations + fanouts). The Hatchet token is stored in AWS SSM Parameter Store. Worker tasks get IAM-based S3 access automatically via SST's resource linking.

If `USE_PREBUILT_IMAGE=true`, SST references the ECR image directly (fast). Otherwise it builds from the Dockerfile during deploy (slower but no push step needed).

### Tear down

```sh
npx sst remove --stage benchmark
```

## Deadlock Safety

The fanout workers need enough slots to support all concurrent scatter/gather nodes in the tree without deadlocking. The formal requirement is at least one more slot than the total number of non-terminal scatter/gather nodes. For the deepest configuration in the suite (factor=2, max_depth=6), this is 63 internal nodes followed by 64 terminal nodes.  The benchmarks were run with 64 collector nodes each with 4 task slots.
