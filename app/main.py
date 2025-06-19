import asyncio

import structlog

from .log import setup_logging
from .task_test import add_one

setup_logging()

logger = structlog.stdlib.get_logger(__name__)


async def main() -> None:
    task = await add_one.kiq(1)
    # Wait for the result.
    result = await task.wait_result(timeout=2)
    print(f"Task execution took: {result.execution_time} seconds.")
    if not result.is_err:
        print(f"Returned value: {result.return_value}")
    else:
        print("Error found while executing task.")


if __name__ == "__main__":
    asyncio.run(main())
