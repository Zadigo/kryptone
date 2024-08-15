import asyncio
from asgiref.sync import sync_to_async
import time


async def method1():
    for _ in range(5):
        print('Method:', 1)
        await asyncio.sleep(5)


async def method2():
    for _ in range(5):
        print('Method:', 2)
        await asyncio.sleep(2)


def method3():
    time.sleep(7)
    print(3)


async def main():
    # await method1()
    # await method2()

    # try:
    #     async with asyncio.timeout(4):
    #         await method1()
    #         await method2()
    # except asyncio.TimeoutError:
    #     print('Timed out')

    # try:
    #     async with asyncio.timeout(None) as c:
    #         new_timeout = asyncio.get_running_loop().time() + 10
    #         c.reschedule(new_timeout)

    #         await method1()
    #         await method2()
    # except asyncio.TimeoutError:
    #     print('Timed out')
    # else:
    #     if c.expired():
    #         print("Didn't finish in time")

    # loop = asyncio.get_running_loop()
    # timeout = loop.time() + 20
    # try:
    #     async with asyncio.timeout_at(timeout):
    #         await method1()
    #         await method2()
    # except asyncio.TimeoutError:
    #     print("Timed out")

    # try:
    #     await asyncio.wait_for(method1(), timeout=3)
    # except asyncio.TimeoutError:
    #     print('Timed out')

    # aws = [asyncio.create_task(method1()), asyncio.create_task(method2())]
    # done, pending = await asyncio.wait(aws, return_when=asyncio.FIRST_COMPLETED)
    # print(done, pending)

    # async with asyncio.TaskGroup() as t:
    #     await t.create_task(method1())
    #     await t.create_task(method2())

    # t1 = asyncio.create_task(method1())
    # t2 = asyncio.create_task(method2())
    # await t1
    # await t2

    # aws = [method1(), method2()]
    # for aw in asyncio.as_completed(aws):
    #     await aw

    # await asyncio.gather(method1(), method2())
    # await asyncio.gather(
    #     asyncio.create_task(method1()),
    #     asyncio.create_task(method2()),
    # )

    # await sync_to_async(method3)()
    pass


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
