from typing import final
from urllib.parse import quote, urlencode
from kryptone.base import SiteCrawler
import time
import random
from kryptone import logger
from kryptone.contrib.models import GoogleSearch


class GoogleSearchMixin(SiteCrawler):
    start_url = "https://www.google.com/search?q=site%3Alinkedin.com%2Fin+Undiz"
    # start_url = 'https://www.google.com/search'
    # query = 'site:linkedin.com/in Undiz'
    container = []

    class Meta:
        crawl = False

    def get_start_url(self):
        query = quote(self.query)
        encoded_query = urlencode({'q': query})
        return f'{self.start_url}?{encoded_query}'

    def post_navigation_actions(self, current_url, **kwargs):
        element = self.evaluate_xpath(
            '//button/div[contains(text(), "Tout accepter")]/..')
        try:
            element.click()
        except:
            pass

    def current_page_actions(self, current_url, **kwargs):
        has_next = True
        while has_next:
            state, next_element = self.driver.execute_script(
                """
                const element = document.querySelector('.AaVjTc').querySelector('td a#pnnext')
                return [element !== null, element]
                """
            )
            has_next = state

            data = self.driver.execute_script(
                """
                const search = document.querySelectorAll('div[id="search"] div[class="MjjYud"]')
                Array.from(search).map((item) => {
                    const title = item.querySelector('h3') && item.querySelector('h3').textContent
                    const url = item.querySelector('a') && .querySelector('a').href
                    return {
                        title,
                        url
                    }
                })
                """
            )
            self.container.append(GoogleSearch(**data))
            print(self.container)

            try:
                next_element.click()
            except:
                logger.error('Could not complete next')
            finally:
                time.sleep(random.randrange(10, 40))
