import structlog
from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker

from app.log import setup_logging
from app.settings import settings

setup_logging()
logger = structlog.stdlib.get_logger("radar.taskiq")

url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
broker = RedisStreamBroker(url=url).with_result_backend(
    RedisAsyncResultBackend(redis_url=url),
)


scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)
