# import asyncio
# import json
# import threading

# import quart
# from quart import copy_current_websocket_context, websocket
# from quart_cors import cors

# from kryptone.base import BaseCrawler, SinglePageAutomater
# from kryptone.server.connections import RedisConnection

# PUBLICATION_CHANNEL = 'kryptone_channel'

# app = quart.Quart(__name__)
# app = cors(
#     app,
#     allow_headers=['content-type', 'authorization'],
#     allow_origin=['http://127.0.0.1:5000', 'http://127.0.0.1:5500'],
#     allow_credentials=True
# )


# redis = RedisConnection().get_connection

# # https://www.metal3d.org/blog/2020/de-flask-%C3%A0-quart/


# async def manage(data, queue):
#     # crawler = BaseCrawler()
#     # crawler.start_url = 'http://example.com'
#     # thread = threading.Thread(target=crawler.start, kwargs={})

#     # automater = SinglePageAutomater()
#     # automater.start_urls = 'http://example.com'
#     # thread = threading.Thread(target=automater.start)
#     # try:
#     #     thread.start()
#     # finally:
#     #     thread.join()
#     print('m', data, queue)


# async def ping(queue):
#     while True:
#         await asyncio.sleep(5)
#         await queue.put({"response": "ping"})


# @app.websocket('/ws/scraper')
# async def schedule_task():
#     queue = asyncio.Queue()

#     @copy_current_websocket_context
#     async def receive_data():
#         while True:
#             message = await websocket.receive()
#             print('b', message)
#             await manage(json.loads(message), queue)

#     @copy_current_websocket_context
#     async def send_data():
#         while True:
#             data = await queue.get()
#             print('a', json.dumps(data))
#             await websocket.send(json.dumps(data))

#     producer = asyncio.ensure_future(send_data())
#     consumer = asyncio.ensure_future(receive_data())
#     pinger = asyncio.ensure_future(ping(queue))

#     try:
#         await asyncio.gather(producer, consumer, pinger)
#     finally:
#         producer.cancel()
#         consumer.cancel()
#         pinger.cancel()


# if __name__ == '__main__':
#     app.run(host='127.0.0.1', port=8000)

import subprocess

from twisted.application.internet import TCPServer, TimerService
from twisted.application.service import Application
from twisted.cred.portal import Portal
from twisted.python import log
from twisted.web import server
from twisted.web.guard import BasicCredentialFactory, HTTPAuthSessionWrapper
from twisted.internet import protocol, reactor
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.internet.interfaces import IAddress
from twisted.internet.protocol import Protocol, ServerFactory, ClientFactory, Factory


# class BaseServer(Protocol):
#     def connectionMade(self):
#         self.transport.write(b'google')

#     def dataReceived(self, data):
#         print(data)


# class _Factory(Factory):
#     def buildProtocol(self, addr):
#         return BaseServer()


# if __name__ == '__main__':
#     endpoint = TCP4ClientEndpoint(reactor, '127.0.0.1', 8123)
#     endpoint.connect(_Factory())
#     reactor.run()


from twisted.internet import reactor
from twisted.web import server
from twisted.web.static import File
from twisted.web.resource import WebSocketProtocol, WebSocketFactory


class MyWebSocketProtocol(WebSocketProtocol):
    def onOpen(self):
        print("WebSocket connection opened")

    def onMessage(self, payload, isBinary):
        if not isBinary:
            message = payload.decode("utf-8")
            print(f"Received message: {message}")
            # Process the message as needed


resource = WebSocketFactory(MyWebSocketProtocol)
site = server.Site(resource)
reactor.listenTCP(8080, site)
reactor.run()
