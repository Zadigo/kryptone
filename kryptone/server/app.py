import asyncio
import json
import threading

import quart
from quart_cors import cors, websocket_cors
from quart import copy_current_websocket_context, jsonify, request, websocket

from kryptone.conf import settings
from kryptone.registry import registry
from kryptone.server.connections import RedisConnection

PUBLICATION_CHANNEL = 'kryptone_channel'

app = quart.Quart(__name__)
app = cors(
    app,
    allow_headers=['content-type', 'authorization'],
    allow_origin=['http://127.0.0.1:5000', 'http://127.0.0.1:5500'],
    allow_credentials=True
)


redis = RedisConnection().get_connection


# async def handle_redis_message(message):
#     pass


# async def redis_listener():
#     with app.app_context():
#         channel = redis.pubsub()
#         channel.subscribe(PUBLICATION_CHANNEL)

#         for message in channel.listen():
#             await handle_redis_message(message)


# @app.before_first_request
# async def start_redis_listener():
#     thread = threading.Thread(target=redis_listener)
#     thread.start()


# https://www.metal3d.org/blog/2020/de-flask-%C3%A0-quart/

async def manage(data, queue):
    pass


async def ping(queue):
    while True:
        await asyncio.sleep(5)
        await queue.put({"response": "ping"})

# @app.route('/schedule')

@app.websocket('/ws/scraper')
async def schedule_task():
    queue = asyncio.Queue()
    
    @copy_current_websocket_context
    async def receive_data():
        while True:
            message = await websocket.receive()
            await manage(json.loads(message), queue)

    @copy_current_websocket_context
    async def send_data():
        while True:
            data = await queue.get()
            await websocket.send(json.dumps(data))

    producer = asyncio.ensure_future(send_data())
    consumer = asyncio.ensure_future(receive_data())
    pinger = asyncio.ensure_future(ping(queue))

    try:
        await asyncio.gather(producer, consumer, pinger)
    finally:
        producer.cancel()
        consumer.cancel()
        pinger.cancel()

    return jsonify({})


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000)
