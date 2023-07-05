import threading

import quart
from quart import jsonify, request

from kryptone.conf import settings
from kryptone.server.connections import RedisConnection

PUBLICATION_CHANNEL = 'kryptone_channel'

app = quart.Quart(__name__)

redis = RedisConnection().get_connection()


async def handle_redis_message(message):
    pass


async def redis_listener():
    with app.app_context():
        channel = redis.pubsub()
        channel.subscribe(PUBLICATION_CHANNEL)

        for message in channel.listen():
            await handle_redis_message(message)


@app.before_first_request
async def start_redis_listener():
    thread = threading.Thread(target=redis_listener)
    thread.start()


@app.route('/create')
async def create_new_task():
    data = await request.form
    url = data['url']
    redis.publish(PUBLICATION_CHANNEL, url)
    return jsonify({})
