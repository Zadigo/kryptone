from kryptone.crawlers.google_maps import generate_search_url
from kryptone.utils.urls import URLFile

urls = [
    URLFile(processor=generate_search_url)
]
