import asyncio
import requests
from bs4 import BeautifulSoup

# https://pgjones.gitlab.io/quart/tutorials/chat_tutorial.html


async def main(*urls):
    urls_to_visit = set(urls)

    queue = asyncio.Queue()

    async def function1():
        while urls_to_visit:
            url = urls_to_visit.pop()
            response = requests.get(url)
            await queue.put(response)
            print('Added response')
            print(url, urls_to_visit)
            await asyncio.sleep(5)

    async def function2():
        while True:
            response = await queue.get()
            print('Queue', queue, response)
            soup = BeautifulSoup(response.content, 'html.parser')
            print(soup.text)
            await asyncio.sleep(10)
            if queue.empty():
                break
    await asyncio.gather(function1(), function2())


if __name__ == '__main__':
    asyncio.run(main('http://example.com', 'http://example.com/1'))
