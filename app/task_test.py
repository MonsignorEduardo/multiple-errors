import structlog

from .tkq import broker

logger = structlog.stdlib.get_logger(__name__)


@broker.task
async def add_one(value: int) -> int:
    logger.info("Adding one to the value", value=value)
    return value + 1
