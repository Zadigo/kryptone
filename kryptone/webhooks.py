import asyncio

from requests import Session
from requests.auth import HTTPBasicAuth
from requests.models import Request
from kryptone.utils.iterators import iterate_chunks
from kryptone import logger


class BaseWebhook:
    """Base class that defines attributes
    for sending requests to a set of webhooks"""

    base_url = None
    scheduled_sending_queue = asyncio.Queue()

    def __init__(self, *, url=None, auth_token_name='Bearer', auth_token=None):
        self.current_iteration = 0
        self.session = Session()
        # self.current_slice = [0, self.base_pagination]
        self.response = None
        self.base_url = url
        self.auth_token_name = auth_token_name
        self.auth_token = auth_token

    def __repr__(self):
        return f'<{self.__class__.__name__}[{self.current_iteration}]>'

    async def create_request(self, data, headers):
        request = Request(
            method='post',
            url=self.base_url,
            json=data,
            headers=headers,
            auth=None
        )
        return self.session.prepare_request(request)
    
    async def create_headers(self):
        headers = {
            'User-Agent': 'Kryptone/JSONCrawler',
            'Content-Type': 'application/json'
        }
        if self.auth_token is not None:
            headers.update(
                {
                    'Authorization': f'{self.auth_token_name} {self.auth_token}'
                }
            )
        return headers

    async def send(self, data):
        headers = await self.create_headers()
        prepared_request = await self.create_request(data, headers)

        try:
            self.response = self.session.send(prepared_request)
        except:
            # Fail silently if a webook cannot be sent
            logger.critical(f'Webhook failed for url: {self.base_url}')
        else:
            logger.info(f'Webhook completed for url: {self.base_url}')
            self.current_iteration = self.current_iteration + 1

    async def iter_send(self, data, chunks=100, wait_time=10):
        """Sends chunks of data to the webhook"""
        chunks_of_data = iterate_chunks(data, n=chunks)
        await self.scheduled_sending_queue.put(chunks_of_data)

        while True:
            while not self.scheduled_sending_queue.empty():
                d = await self.scheduled_sending_queue.get()

                async def timed_send(chunked_data):
                    response = await self.send(chunked_data)
                    asyncio.sleep(wait_time)
                    return response

                tasks = []
                for chunked_data in chunks_of_data:
                    task = asyncio.create_task(timed_send(chunked_data))
                    tasks.append(task)

                self.responses = await asyncio.gather(tasks)


class Webhook(BaseWebhook):
    """Base class to send a request to a webhook
    over the internet"""


class Webhooks:
    """Manage requests for multiple webhooks"""

    def __init__(self, urls):
        self.webhooks = []
        self.responses = []

        for i, url in enumerate(urls):
            instance = Webhook(url=url)
            instance.current_iteration = i
            self.webhooks.append(instance)

    def __repr__(self):
        return f'<{self.__class__.__name__}[count={len(self.webhooks)}]>'

    async def resolve(self, data):
        tasks = []

        async def resolver(webhook):
            if not isinstance(webhook, Webhook):
                raise ValueError(f'{webhook} should be an instance of Webhook')
            
            await webhook.send(data)
            return webhook.response

        for webhook in self.webhooks:
            task = asyncio.create_task(resolver(webhook))
            tasks.append(task)

        self.responses = await asyncio.gather(*tasks)
