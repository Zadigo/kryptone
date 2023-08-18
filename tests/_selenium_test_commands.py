import asyncio
import time

from selenium.webdriver import Edge
from webdriver_manager.microsoft import EdgeChromiumDriverManager

driver = Edge(EdgeChromiumDriverManager().install())


async def main():
    driver.get('http://example.com')
    result = driver.execute_async_script("""
    var callback = arguments[arguments.length - 1]
    window.setTimeout(() => {
        const title = document.querySelector('title').textContent
        callback(title)
    }, 3000)
    """)
    print(result)
    time.sleep(5)
    driver.quit()

if __name__ == '__main__':
    asyncio.run(main('http://example.com/1', 'http://example.com/2'))
