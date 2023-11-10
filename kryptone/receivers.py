from selenium.webdriver.common.by import By

from kryptone import logger
from kryptone.utils.iterators import JPEGImagesIterator


def collect_images_receiver(sender, current_url=None, **kwargs):
    """Collects every images present on the
    actual webpage and classifies them"""
    try:
        image_elements = sender.driver.find_elements(By.TAG_NAME, 'img')
    except:
        pass
    else:
        instance = JPEGImagesIterator(current_url, image_elements)
        logger.info(f'Collected {len(instance)} images')
