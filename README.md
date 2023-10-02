# Kryptone

A web scapper dedicated to marketers and wrapped around the Selenium library

## How it works

### Web crawling

The spider starts from an initial page and gathers all the urls. Each url is added in the `urls_to_visit` container.

It then repeats the process until the first container is emptied. When a page is successfully visited, the url is added to the `visited_urls` container.

### Page automation

If you want to automate certain steps on a single page or a group or different pages, use the `SinglePageAutomater`. The code written under the `run_actions` functions will be executed on each specified url.

## How to use

### Starting a project

The easiest way to use Kryptone is by starting a project through `python -m krytpone start_project`. You can read the hiearchy of a project below.

```bash
├── project
│   ├── media
│   │   ├── /**/*.json
│   │   ├── /**/*.jpeg
│   ├── cache.json
│   ├── kryptone.log
│   ├── automaters.py
│   ├── manage.py
│   ├── models.py
│   ├── settings.py
│   └── spiders.py
```

Projects are self contained in order to efficiently separate each crawling methods. Though a project can contain multiple spiders, it is advised to regroup your spiders by theme in order to organize the massive amount of data that could be collected through one or multiple runs.

### Crawling a website

You need to define an entrypoint from which the spider will start gathering urls. Once the urls added to urls to visit, the spider will move to the next page after the wait time completed.

```python
from kryptone.base import BaseCrawler

class MyWebscrapper(BaseCrawler):
    start_url = 'http://example.com'
```

### Page actions

Once the spider visits a page, two types of actions can be performed on the page: `post_visit_actions` and `run_actions`.

`post_visit_actions` are actions performed just after the spider has visited a page. For instance, say you need to click on cookie consent screen immediately after visiting a page, you could do the following.

#### Post visit actions

A post visit action is an action that is executed immediately after the robot has visited a specific page. For instance, clicking a cookie consent button on a banner can be considered a post visit action.

```python
from kryptone.base import BaseCrawler

class MyWebscrapper(BaseCrawler):
    start_url = 'http://example.com'

    def post_visit_actions(self, **kwargs):
        self.click_consent_button(element_id='button')
```

#### User actions

These actions are executed once all urls are gathered on the page and before the robot is ready to move to a different one. It will execute logic within this method on every page.

```python
from kryptone.base import BaseCrawler

class MyWebscrapper(BaseCrawler):
    start_url = 'http://example.com'

    def run_actions(self, current_url, **kwargs):
        # Do something here
        pass
```

__What does current url stand for__

`current_url` is an instance of `URL` in `kryptone.utils.URL` which implements a set of additional methods on the url string.

* `is_path` checks that the url is a path
* `is_valid` checks that the url starts with _http_
* `has_fragment` checks that the url contains a fragment
* `create` will create a new url instance
* `is_file` checks that the url points to a file
* `as_path` returns the url as a `pathlib.Path`
* `get_extension` returns the urls extension (e.g. pdf) if present
* `is_same_domain` compares two urls and determines if they are from the same domain
* `get_status` sends a request to determine validity
* `compare` compares two urls
* `capture` captures an element in the url using regex
* `test_path` tests if the url's path passes a regex test
* `decompose_path` decompose the path into a list

### Filtering urls

Urls gathered on the page can be filtered. This process is executed just before they are added to `urls_to_visit` container.

This is very useful in situations where we want to ignore certain pages that would be useless for crawling. Filtereing urls is done with `URLPassesTest` and `UrlPassesRegexTest`.

For instance , let's say we want to avoid any url that contains `/shirts/`:

```python
from kryptone.base import BaseCrawler
from kryptone.utils.urls import URLPassesTest

class MyScrapper(BaseCrawler):
    start_url = 'http://example.com'
    
    class Meta:
        url_passes_tests = [
            URLPassesTest('base_pages', paths=[
                '/shirts/'
            ])
        ]
```

```python
from kryptone.base import BaseCrawler
from kryptone.utils.urls import URLPassesTest

class MyScrapper(BaseCrawler):
    start_url = 'http://example.com'
    
    class Meta:
        url_passes_tests = [
            UrlPassesRegexTest('base_pages', regex=r'^\/shirts\/')
        ]
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

If you started a previous crawl and need to continue from a set of urls that were initially gathered, call this method.

#### Starting from a website's XML sitemap

Most times, the most interesting method to crawl the important pages of a website is via it's sitemap. The publisher indicates the pages that should be indexed which can make crawling a lot more efficient than a random url entrypoint.

#### Starting from a website's HTML sitemap

Some websites will have user friendly sitemap to facilitate navigation. This can also be used as an entrypoint.

## Project commands

This is the list of available project commands for Krytpone.

### Create task

### Healthcheck

### Run server

### Start project

Creates a new project in the local directory from which the command was called.

### Start

Launches the spiders registered in `SPIDERS` in the settings file.

### Test project

Tests that a given project can be launched. This is an integrity check.

## Models

Storing data is the second most important step when crawling a website. Kryptone comes with a set of pre-built models which are based on the default `dataclass` python library.

## Caching

Kryptone uses two type of caching mechanisms by default:

* File
* Redis

### File

This means that everytime the list of urls are updated, the `cache.json` file is also updated. Caching allows to resume crawling if necessary when/if an exception occurs during runs.

### Redis

If a connection exists, temporary elements are stored in the Redis database backend. The backend is not to be exposed to the internet and should not be exposed if sensitive data will be persisted.

### Memcache

Is used in the same logic as Redis.

## Signals

Krytpone uses signals at certain given steps in order to run additional actions.

### Navigation

Signal used to indicate that a navigation has occured.

### Collect images

Everytime a page is visited, the images are collected. This is a default action that can stopped in the settings file e.g `COLLECT_IMAGES`.

### Custom signals

You can create custom signals in two different manners. The first manner requires that you have functions or callable classes that can be used a receivers. They need to be connected to your custom signal.

```python
from kryptone.signals import Signal

my_signal = Signal()


def some_receiver(url):
    pass


class MyScrapper(BaseCrawler):
    start_url = 'http://example.com'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        my_signal.connect(my_signal, sender=self)
```

The second method below will connect your custom signal to a custom receiver and every time the signal is called, the receivers in the `my_signal` pool will be triggered.

```python
from kryptone.signals import Signal

my_signal = Signal()


class MyScrapper(BaseCrawler):
    start_url = 'http://example.com'


@function_to_receiver(my_signal)
def custom_receiver(url):
    pass
```

## Utilities

### TestUrl

This class takes two urls and determines if they are similar.

```python

result = TestUrl('http://example.com', 'http://example.com')

> True
```

## Monitoring

Your spiders can be monitered in multiple ways. The custom monitoring method used by Kryptone is emailing. If an emailing system is present in your project, Kryptone will use this for any detected failure. Exceptions are bubbled up so you can have a precise idea of what exactly went wrong in your project.

## Settings

You can specify a wait time for which the web scrapper is supposed to wait until going to the next page.

__PROJECT_PATH__

Determines the absolute path the local project

__SPIDERS__

Lists the spiders to run for the project

__WEBDRIVER__

The browser's name to use for crawling pages

__MEDIA_FOLDER__

The name of the media folder to use

__WAIT_TIME__

The amount of time to wait before moving the to the next page

__WAIT_TIME_RANGE__

The random amount of time to wait from the range before moving to the next page

__CACHE_FILE_NAME__

The name of the cache file to use for storing visited urls and urls to visit

__ACTIVE_STORAGE_BACKENDS__


__STORAGE_BACKENDS__


__EMAIL_HOST__


__EMAIL_PORT__


__EMAIL_HOST_USER__


__EMAIL_HOST_PASSWORD__


__EMAIL_USE_TLS__


__DEFAULT_FROM_EMAIL__


__WEBSITE_LANGUAGE__

The language the of the visited website
