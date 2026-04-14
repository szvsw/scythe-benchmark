from scythe.worker import ScytheWorkerConfig

from experiments import *  # noqa: F403

if __name__ == "__main__":
    worker_config = ScytheWorkerConfig()
    worker_config.start()
