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

### Filtering urls

Urls can be filtered by passing in a filter function in `url_filters`. This function should always return a boolean.

The url filtering functions a run consecutively 

For instance , let's say we want to avoid any url that contains `/shirts/`:

```python

def avoid_shirts(url):
    if '/shirts/' in url:
        return False
    return True


class MyScrapper(BaseCrawler):
    start_url = 'http://example.com'
    url_filters = [avoid_shirts]
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
