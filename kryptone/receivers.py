from selenium.webdriver.common.by import By

from kryptone import logger
from kryptone.utils.iterators import JPEGImagesIterator


def collect_images_receiver(sender, current_url=None, **kwargs):
    """Collects every images present on the actual webpage 
    and classifies them"""
    pass
    # images = sender.driver.execute_script("""return document.querySelectorAll('img')""")
    # instance = JPEGImagesIterator(current_url, images)
    # logger.info(f'Collected {len(instance)} image(s)')
