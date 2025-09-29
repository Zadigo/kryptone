import celery
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

@celery.shared_task
def test_task():
    logger.info("Test task started")
