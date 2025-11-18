import celery
import atexit
import signal
import subprocess
from kryptone.conf import settings


def get_broker():
    user = getattr(settings, 'RABBITMQ_USER', 'guest')
    password = getattr(settings, 'RABBITMQ_PASSWORD', 'guest')
    host = getattr(settings, 'RABBITMQ_HOST', 'localhost')
    port = getattr(settings, 'RABBITMQ_PORT', 5672)
    return f"amqp://{user}:{password}@{host}:{port}//"


def get_backend():
    host = getattr(settings, 'REDIS_HOST', 'localhost')
    port = getattr(settings, 'REDIS_PORT', 6379)
    return f"redis://{host}:{port}/0"


app = celery.Celery(
    'kryptone',
    broker=get_broker(),
    backend=get_backend(),
    log=None
)

# print(vars(settings))

app.autodiscover_tasks(
    [
        'kryptone.core.tasks',
        getattr(settings, '_PYTHON_PATH', '') + '.tasks'
    ]
)


def create_celery_server(spider_config):
    """Create a celery server instance that will be used to run tasks
    in the background while the spider is running.
    """
    # app.start(argv=['worker', '--loglevel=info'])
    celery_process = subprocess.Popen(
        [
            'celery',
            '-A',
            'kryptone.core.servers.app',
            'worker',
            '--loglevel=info'
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    def stop_server():
        celery_process.send_signal(signal.SIGTERM)
        celery_process.wait()

    atexit.register(stop_server)
    return celery_process
