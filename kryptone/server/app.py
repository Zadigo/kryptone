import threading

import quart

from kryptone.conf import settings

app = quart.Quart(__name__)


async def handle_redis_message(message):
    pass


async def redis_listener():
    await handle_redis_message(message)


@app.before_first_request
async def start_redis_listener():
    thread = threading.Thread(target=redis_listener)
    thread.start()


@app.route('/create')
async def create_new_task():
    pass
