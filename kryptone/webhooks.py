import asyncio

from requests import Session
from requests.auth import HTTPBasicAuth
from requests.models import Request

from kryptone import logger
from kryptone.conf import settings


class BaseWebhook:
    """Base class that defines attributes
    for sending requests to a set of webhooks"""

    base_url = None

    def __init__(self, *, url=None, auth_token_name='Bearer', auth_token=None):
        self.current_iteration = 0
        self.session = Session()
        self.base_pagination = settings.WEBHOOK_PAGINATION
        self.current_slice = [0, self.base_pagination]
        self.response = None
        self.base_url = url
        self.auth_token_name = auth_token_name
        self.auth_token = auth_token

    def __repr__(self):
        return f'<{self.__class__.__name__}[{self.current_iteration}]>'

    def send(self, data):
        headers = {'Content-Type': 'application/json'}
        if self.auth_token is not None:
            headers.update(
                {'Authorization': f'{self.auth_token_name} {self.auth_token}'})

        request = Request(
            method='post',
            url=self.base_url,
            data=data,
            headers=headers,
            auth=None
        )
        prepared_request = self.session.prepare_request(request)

        try:
            self.response = self.session.send(prepared_request)
        except:
            logger.critical(f'Webhook failed for url: {self.base_url}')
        else:
            if self.current_iteration > 0:
                # Update the slice so that we can get the data from
                # a given section to another one
                self.current_slice[0] = self.current_slice[0] + \
                    self.base_pagination
                self.current_slice[1] = self.current_slice[1] + \
                    self.base_pagination

            logger.info(f'Webhook completed for url: {self.base_url}')
            self.current_iteration = self.current_iteration + 1


class Webhook(BaseWebhook):
    """Base class to send a request to a webhook
    to the internet"""


class Webhooks:
    """Manage requests for multiple webhooks"""

    def __init__(self, urls):
        self.webhooks = []
        self.responses = []
        for url in urls:
            self.webhooks.append(Webhook(url=url))

    def __repr__(self):
        return f'<{self.__class__.__name__}[count={len(self.webhooks)}]>'

    async def resolve(self, data):
        tasks = []

        async def resolver(webhook):
            webhook.send(data)
            return webhook.response

        for webhook in self.webhooks:
            task = asyncio.create_task(resolver(webhook))
            tasks.append(task)

        self.responses = await asyncio.gather(*tasks)


# w = Webhooks(['http://example.com', 'http://example.com'])
# asyncio.run(w.resolve([]))
# print(w.webhooks)
