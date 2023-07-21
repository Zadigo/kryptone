# Kryptone

A web scapper dedicated to marketers and wrapped around the Selenium library

## How it works

### Web crawling

The spider starts from an initial page and gathers all the urls. Each url is added in the `urls_to_visit` container.

It then repeats the process until the first container is emptied. When a page is successfully visited, the url is added to the `visited_urls` container.

### Page automation

If you want to automate certain steps on a single page or a group or different pages, use the `SinglePageAutomater`. The code written under the `run_actions` functions will be executed on each specified url.

## How to use

### Crawling a website

First you need to define an entrypoint from which the spider will start gathering urls. One the urls added to urls to visit, the spider will move to the next page after the wait time completed.

```python
from kryptone.base import BaseCrawler

class MyWebscrapper(BaseCrawler):
    start_url = 'http://example.com'
```

### Page actions

Once the spider visits a page, two types of actions can be performed on the page: `post_visit_actions` and `run_actions`.

`post_visit_actions` are actions performed just after the spider has visited a page. For instance, say you need to click on cookie consent screen immediately after visiting a page, you could do the following.

#### Post visit actions

A post visit action is action that is executed immediately after the robot has visited a specific page. For instance, clicking a cookie consent page can be considered a post visit action.

```python
from kryptone.base import BaseCrawler

class MyWebscrapper(BaseCrawler):
    start_url = 'http://example.com'

    def post_visit_actions(self, **kwargs):
        self.click_consent_button(element_id='button')
```

### User actions

These actions are executed once all urls are gathered on the page and before the robot is ready to move to a different page.

```python
from kryptone.base import BaseCrawler

class MyWebscrapper(BaseCrawler):
    start_url = 'http://example.com'

    def run_actions(self, **kwargs):
        # Do something here
        pass
```

### Filtering urls

Urls gathered on the page can be filtered. This process is executed just before they are add to `urls_to_visit` container.

This is very useful in situations where we want to ignore certain pages that would be useless for crawling.

Your filtering functions should always return a boolean. They are also executed consecutively in the order in which they were implemented.

If a filter fails by not returning a boolean, the url is considered to be valid.

For instance , let's say we want to avoid any url that contains `/shirts/`:

```python
from kryptone.base import BaseCrawler

def avoid_shirts(url):
    if '/shirts/' in url:
        return False
    return True


class MyScrapper(BaseCrawler):
    start_url = 'http://example.com'
    url_filters = [avoid_shirts]
```

__Understanding how urls are gathered__

When the spider goes on a given page, all the urls are gathered regardless of their types:

* http://example.com
* http://example.com/path#
* http://example.com/
* http://example.com?q=celebrity
* /example.com
* http://another-domain.com
* http://example.com/some-image.png

As you might observe, not all these urls are particularly interesting to us. Therefore, a set of built-in features are implemented to ensure that the spider does not gather any types of elements.

First, it will ensure that the urls are always part of the same domain as the url that was used as the entrypoint.

Second, it will avoid visiting duplicate urls. For instance, only one version of `http://example.com` will be visited. The same reasoning applies if an url was already visited.

Third, blank or incorrect links are completely ignored.

Fragments and urls that finish with `/` are also ignored since they are the exact same version of a page.

Finally, incomplete paths are reconstructed using initial domain.

### How the spider starts

The main method for starting the spider is `start`. However, there are three other methods to initiate the crawling loop:

* resume
* start_from_sitemap_xml
* start_from_html_sitemap

#### Resuming a previous crawl

If you have started a previous crawl and need to continue from a set of urls that were initially gathered, call this method.

#### Starting from a website's XML sitemap

Most times, the most interesting method to crawl the important pages of a website is via it's sitemap. The publisher indicates the pages that should be indexed which can make crawling a lot more efficient than a random url entrypoint.

#### Starting from a website's HTML sitemap

Some websites will have user friendly sitemap to facilitate navigation. This can also be used as an entrypoint.

## Models

Storing data is the second most important step when crawling a website. Kryptone comes with a set of pre-built models which are based on the default `dataclass` python library.

## Signals

Krytpone uses signals at certain given steps which can be also used to run additional actions.

## Settings

You can specify a wait time for which the web scrapper is supposed to wait until going to the next page.

__PROJECT_PATH__


__SPIDERS__


__AUTOMATERS__


__WEBDRIVER__


__MEDIA_FOLDER__


__WAIT_TIME__


__WAIT_TIME_RANGE__


__CACHE_FILE_NAME__


__ACTIVE_STORAGE_BACKENDS__


__STORAGE_BACKENDS__


__EMAIL_HOST__


__EMAIL_PORT__


__EMAIL_HOST_USER__


__EMAIL_HOST_PASSWORD__


__EMAIL_USE_TLS__


__DEFAULT_FROM_EMAIL__


__WEBSITE_LANGUAGE__
