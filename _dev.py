# from kryptone.base import SiteCrawler
# from kryptone.utils.urls import URL


# class CustomCrawler(SiteCrawler):
#     start_url = 'http://example.com'

#     class Meta:
#         crawl = True


# instance = CustomCrawler(browser_name='edge')
# instance.start()

from kryptone.utils.urls import MultipleURLManager
import time

urls = [
    'http://example.com',
    'http://example.com/1'
]
instance = MultipleURLManager(start_urls=urls)
while instance._urls_to_visit:
    url = instance.get()
    instance.append_multiple(['http://example.com/2'])
    print(url)

print(instance.dataframe)
