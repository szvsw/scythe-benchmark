# Scythe Subdivision Benchmark

Benchmark suite measuring how scatter/gather tree subdivision depth and branching factor affect total wall-clock time to solution in [Scythe](https://github.com/szvsw/scythe).

This addresses the question: does recursively subdividing a large pool of tasks into a tree of scatter/gather nodes improve throughput compared to dispatching all tasks from a single node?

## Benchmark Design

All cases dispatch **N = 1023** leaf tasks with a 0.5s sleep per task. The suite varies `factor` (branching factor) and `max_depth` (recursion depth) across 15 configurations, each repeated 5 times (75 total runs):

| `--factor` | `--max-depth` | Terminal nodes |
|------------|---------------|----------------|
| 0          | 0             | 1 (no subdivision) |
| 2          | 1             | 2              |
| 2          | 2             | 4              |
| 2          | 3             | 8              |
| 2          | 4             | 16             |
| 2          | 5             | 32             |
| 2          | 6             | 64             |
| 4          | 1             | 4              |
| 4          | 2             | 16             |
| 4          | 3             | 64             |
| 8          | 1             | 8              |
| 8          | 2             | 64             |
| 16         | 1             | 16             |
| 32         | 1             | 32             |
| 64         | 1             | 64             |

This explores the two-dimensional parameter space (factor x depth) and allows comparing configurations that produce the same number of terminal nodes via different tree shapes.

## Prerequisites

- [uv](https://astral.sh/uv) package manager
- [Docker](https://docs.docker.com/get-docker/) (with Docker Compose v2)
- A [Hatchet Cloud](https://cloud.hatchet.run) account with an API token
- An S3 bucket with AWS credentials
- [AWS CLI](https://aws.amazon.com/cli/) (for cloud deployment)
- [Node.js](https://nodejs.org/) (for SST, cloud deployment only)

### Install dependencies

```sh
make install
```

## Cloud Deployment (AWS ECS) — Primary

The published benchmark results were produced using this cloud deployment path. Workers run on AWS ECS Fargate (spot instances by default), provisioned via [SST](https://sst.dev) infrastructure-as-code in the `infra/` directory.

### 1. Configure environment

```sh
cd infra
cp .env.example .env
```

Edit `infra/.env` with your AWS account ID, region, Hatchet token, S3 bucket, and desired replica counts (`SIM_COUNT`, `FAN_COUNT`). The published results used 256 simulation workers and 64 fanout workers on Fargate spot capacity.

### 2. Push worker image to ECR (recommended)

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

### 3. Deploy

```sh
cd infra
npx sst deploy --stage benchmark
```

This provisions a VPC, ECS cluster, and two Fargate spot services (simulations + fanouts). The Hatchet token is stored in AWS SSM Parameter Store. Worker tasks get IAM-based S3 access automatically via SST's resource linking.

If `USE_PREBUILT_IMAGE=true`, SST references the ECR image directly (fast). Otherwise it builds from the Dockerfile during deploy (slower but no push step needed).

### 4. Run the benchmark suite

With the cloud workers running, trigger the full suite from your local machine:

```sh
cp .env.example .env
# Edit .env with your Hatchet Cloud token, AWS credentials, and S3 bucket name
make suite
```

This runs all 15 configurations x 5 repeats = 75 benchmark runs sequentially, with a Rich progress display showing overall completion, elapsed time, and estimated time remaining. Results are appended to `results/benchmark.csv`.

### 5. Tear down

```sh
cd infra
npx sst remove --stage benchmark
```

## Local Deployment (Docker Compose) — Testing Only

The local Docker Compose setup is provided for verifying that the experiment code and worker configuration are correct before deploying to the cloud. It is **not** suitable for producing benchmark results, as local Docker containers share the host machine's resources and do not reflect the scaling behavior of a distributed cloud deployment.

### 1. Configure environment

```sh
cp .env.example .env
```

Edit `.env` with your Hatchet Cloud token, AWS credentials, and S3 bucket name.

### 2. Start workers

```sh
make up
```

This starts fanout workers and simulation workers via Docker Compose. Adjust `SIMULATIONS_REPLICAS` to scale:

```sh
SIMULATIONS_REPLICAS=32 docker compose up -d --build
```

### 3. Run a quick test

Run an individual benchmark to verify everything is wired up correctly:

```sh
make bench ARGS="--factor 4 --max-depth 1 --sleep 0.5 --n 1023"
```

### 4. Stop workers

```sh
make down
```

## Running Individual Benchmarks

For one-off runs or custom configurations (works with either local or cloud workers):

```sh
make bench ARGS="--factor 16 --max-depth 1 --sleep 0.5 --n 1023"
make bench ARGS="--factor 2 --max-depth 0 --sleep 0 --n 4096 --run-name custom-flat"
```

## Plotting Results

The `plots.ipynb` Jupyter notebook produces publication-quality figures from `results/benchmark.csv`. It generates four plots:

1. **Terminal Nodes vs Total Time** — Dodged scatter with error bars showing mean and individual runs; color encodes depth, marker encodes factor. Configurations sharing a terminal-node count are spread apart horizontally for clarity.
2. **Factor x Depth Heatmap** — Bubble chart where position is (factor, depth), color encodes mean runtime, and size encodes terminal nodes.
3. **Ranked Configurations** — Horizontal bar chart sorted fastest to slowest, with speedup annotations relative to the no-subdivision baseline.
4. **Speedup vs Terminal Nodes** — Speedup factor (baseline time / config time) as a function of terminal nodes.

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

## Deadlock Safety

The fanout workers need enough slots to support all concurrent scatter/gather nodes in the tree without deadlocking. The formal requirement is at least one more slot than the total number of non-terminal scatter/gather nodes. For the deepest configuration in the suite (factor=2, max_depth=6), this is 63 internal nodes followed by 64 terminal nodes. The benchmarks were run with 64 fanout workers each with 4 task slots.
