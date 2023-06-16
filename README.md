# Kryptone

A web scapper dedicated to marketers and wrapped around the Selenium library

## How it works

The scrapper starts from an initial page and gathers all the urls. Each url is added in the `urls_to_visit` container. It then repeats the process until the first container is emptied.

When a page is successfully visited, the url is added to the `visited_urls` container.

## How to use

### Crawling a whole website

```python
class MyWebscrapper(BaseCrawler):
    start_url = 'http://example.com'

scrapper = MyWebscrapper()
scrapper.start()
```

#### Filtering urls

Urls can be filtered via a filter function in `url_filters`. These functions should always return a boolean and they are also run consecutively in the order in which they were implemented.

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

### Automating actions on a single page

If you want to automate certain steps on a single page or a group or different pages, use the `SinglePageAutomater`. The code written under the `run_actions` functions will be executed on each specified url.

## Running actions on each page

### Post visit actions

A post visit action is action that is executed immediately after the robot has visited a specific page. For instance, clicking a cookie consent page can be considered a post visit action.

### User actions

These actions are executed once all urls are gathered on the page and before the robot is ready to move to a different page.

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
