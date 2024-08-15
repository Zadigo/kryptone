import asyncio
from typing import Coroutine, Generator, Literal, Union

import requests
from requests import Session
from requests.models import Response

class BaseWebhook:
    base_url: str = ...
    scheduled_sending_queue: asyncio.Queue = ...
    current_iteration: int = ...
    session = Session()
    base_pagination: int = ...
    current_slice: list[int, int] = ...
    response: Response = ...
    base_url: str = ...
    auth_token_name: str = ...
    auth_token: str = ...

    def __init__(
        self,
        *,
        url: str = ...,
        auth_token_name: str = Literal['Bearer'],
        auth_token: str = ...
    ): ...
    def __repr__(self) -> str: ...

    async def create_request(self, data: Union[list, dict], headers: dict) -> Coroutine[requests.PreparedRequest]: ...
    async def create_headers(self) -> Coroutine[dict[str]]: ...
    async def send(self, data: Union[list[dict], dict]) -> Coroutine[None]: ...
    async def iter_send(self, data: Union[list[dict], dict], chunks: int= ..., wait_time: int=...) -> Coroutine[None]: ...


class Webhook(BaseWebhook):
    ...


class Webhooks:
    webhooks: list[Webhook] = ...
    responses: list[Response] = ...

    def __init__(self, urls: Union[list, tuple, Generator]): ...
    def __repr__(self) -> str: ...
    async def resolve(self, data: Union[list[dict], dict]): ...
