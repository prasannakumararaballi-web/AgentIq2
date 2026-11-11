"""Worker process runner for background asynchronous jobs."""

import asyncio
import logging
from apps.worker.config import worker_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("agentiq.worker")


async def start_worker() -> None:
    """Run the worker event loop listening to background task queues."""
    logger.info("Initializing AgentIQ Worker Process...")
    logger.info(f"Queues: {worker_settings.worker_queues}")
    logger.info(f"Concurrency: {worker_settings.worker_concurrency}")
    # In Phase 2, connect procrastinate app and launch worker loop
    logger.info("Worker process initialized in standby mode (Phase 1).")


if __name__ == "__main__":
    asyncio.run(start_worker())
