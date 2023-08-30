import asyncio
import time

import requests
from bs4 import BeautifulSoup
from selenium.webdriver import Chrome, ChromeOptions, Edge, EdgeOptions
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

# https://pgjones.gitlab.io/quart/tutorials/chat_tutorial.html

driver = Edge(EdgeChromiumDriverManager().install())


async def main(*urls):
    urls_to_visit = set(urls)

    queue = asyncio.Queue()

    async def function1():
        while urls_to_visit:
            url = urls_to_visit.pop()
            response = requests.get(url)
            driver.get(url)
            await queue.put(response)
            print('Added response', url, urls_to_visit)
            await asyncio.sleep(5)

    async def function2():
        while True:
            response = await queue.get()
            # print('Queue', queue, response)
            soup = BeautifulSoup(response.content, 'html.parser')
            print(soup.find('title').text)
            await asyncio.sleep(10)
            if queue.empty():
                break
    await asyncio.gather(function1(), function2())
    driver.quit()


# async def main(*args):
#     async def some_function():
#         for i in range(100):
#             print('function', i)
#             await asyncio.sleep(5)

#     async def other_function():
#         for i in range(100):
#             print('other', i)
#             await asyncio.sleep(2)

#     # task1 = asyncio.ensure_future(some_function())
#     # task2 = asyncio.ensure_future(other_function())

#     tasks = []
#     for x in [some_function, other_function]:
#         tasks.append(asyncio.ensure_future(x()))


#     # await asyncio.gather(task1, task2)
#     await asyncio.gather(*tasks)

# import requests
# import mimetypes
# from kryptone.utils.randomizers import RANDOM_USER_AGENT
# from urllib.parse import urlparse


# async def main():
#     queue = asyncio.Queue()
#     image_urls = [
#         'https://www.jennyfer.com/dw/image/v2/AAQC_PRD/on/demandware.static/-/Sites-jennyfer-catalog-master/default/dwa184efb3/images/10042987C060_81_G.jpg?sw=592',
#         'https://www.jennyfer.com/dw/image/v2/AAQC_PRD/on/demandware.static/-/Sites-jennyfer-catalog-master/default/dw4fc8bc61/images/10042987C060_82_G.jpg?sw=592'
#     ]

#     async def request_images():
#         while image_urls:
#             url = image_urls.pop()
#             headers = {'User-Agent': RANDOM_USER_AGENT()}
#             response = requests.get(url, headers=headers)
#             if response.ok:
#                 url_object = urlparse(url)
#                 mimetype, _ = mimetypes.guess_type(url_object.path)
#                 extension = mimetypes.guess_extension(mimetype)
#                 await queue.put((extension, response.content))
#                 print('Got response for:', response)
#             await asyncio.sleep(2)

#     async def save_image():
#         index = 1
#         while not queue.empty():
#             extension, content = await queue.get()
#             if content is not None:
#                 with open(f'{index}{extension}', mode='wb') as f:
#                     f.write(content)
#                     print('Downloaded image')
#             index = index + 1
#             await asyncio.sleep(4)

#     await asyncio.gather(request_images(), save_image())


if __name__ == '__main__':
    asyncio.run(main('http://example.com/1', 'http://example.com/2'))
    # asyncio.run(main('http://example.com', 'http://example.com/1'))
