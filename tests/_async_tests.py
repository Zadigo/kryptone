import asyncio
import requests
from bs4 import BeautifulSoup

# https://pgjones.gitlab.io/quart/tutorials/chat_tutorial.html


# async def main(*urls):
#     urls_to_visit = set(urls)

#     queue = asyncio.Queue()

#     async def function1():
#         while urls_to_visit:
#             url = urls_to_visit.pop()
#             response = requests.get(url)
#             await queue.put(response)
#             print('Added response')
#             print(url, urls_to_visit)
#             await asyncio.sleep(5)

#     async def function2():
#         while True:
#             response = await queue.get()
#             print('Queue', queue, response)
#             soup = BeautifulSoup(response.content, 'html.parser')
#             print(soup.text)
#             await asyncio.sleep(10)
#             if queue.empty():
#                 break
#     await asyncio.gather(function1(), function2())


async def main(*args):
    async def some_function():
        for i in range(100):
            print('function', i)
            await asyncio.sleep(5)

    async def other_function():
        for i in range(100):
            print('other', i)
            await asyncio.sleep(2)

    # task1 = asyncio.ensure_future(some_function())
    # task2 = asyncio.ensure_future(other_function())

    tasks = []
    for x in [some_function, other_function]:
        tasks.append(asyncio.ensure_future(x()))


    # await asyncio.gather(task1, task2)
    await asyncio.gather(*tasks)


if __name__ == '__main__':
    asyncio.run(main('http://example.com', 'http://example.com/1'))
