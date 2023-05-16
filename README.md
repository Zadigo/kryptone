# Kryptone

A web scapper for marketers wrapped around Selenium

## How it works

The scrapper starts from an initial page and gathers all the urls on said page. Each url is added in the `urls_to_visit` container. Then the web scrapper repeats the process until the first container is emptied.

When the scrapper visits a page, the url is added to the ``visited_urls` container.

## How to use

```python
class MyWebscrapper(BaseCrawler):
    start_url = 'http://example.com'

scrapper = MyWebscrapper()
scrapper.start()
```

## Parameters

### Wait time

You can specify a wait time for which the web scrapper is supposed to wait until going to the next page.


## Url validators

Urls can be validated before getting added to the 

```python
class MyWebscrapper(BaseCrawler):
    start_url = 'http://example.com'

scrapper = MyWebscrapper()
scrapper.start()
```
