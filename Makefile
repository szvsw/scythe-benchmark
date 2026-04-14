.PHONY: up
up: ## Build and start workers
	docker compose up -d --build

.PHONY: down
down: ## Stop workers
	docker compose down

.PHONY: logs
logs: ## Follow worker logs
	docker compose logs -f

.PHONY: bench
bench: ## Run a benchmark (pass ARGS, e.g. make bench ARGS="--factor 256 --max-depth 1")
	uv run --env-file .env benchmark.py $(ARGS)

.PHONY: suite
suite: ## Run the full benchmark suite (all configurations x 5 repeats)
	uv run --env-file .env run_suite.py

.PHONY: docker-login
docker-login: ## Login to ECR (requires AWS CLI + credentials)
	@aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com

.PHONY: push-worker
push-worker:
	@uv run --env-file .env make docker-login
	@docker compose build simulations
	@docker compose push simulations

.PHONY: install
install: ## Install dependencies
	uv sync --all-groups --all-extras

.PHONY: help
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
