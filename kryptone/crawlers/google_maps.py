import csv
import dataclasses
import json
import random
import re
import time
from urllib.parse import quote_plus, urljoin

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from kryptone import logger
from kryptone.app import BaseCrawler, SinglePageAutomater
from kryptone.conf import settings
from kryptone.utils.file_readers import write_csv_document, write_json_document
from kryptone.utils.iterators import drop_null
from kryptone.utils.text import clean_text, parse_price
from kryptone.utils.urls import URLFile


@dataclasses.dataclass
class GoogleBusiness:
    name: str = None
    url: str = None
    address: str = None
    rating: str = None
    number_of_reviews: int = None
    comments: str = None

    @property
    def as_json(self):
        return {
            'name': self.name,
            'url': self.url,
            'address': self.address,
            'rating': self.rating,
            'number_of_reviews': self.number_of_reviews,
            'comments': self.comments
        }
    
    def as_csv(self):
        rows = []
        for comment in self.comments:
            row = [self.name, self.url, self.address, self.rating, 
                   self.number_of_reviews, comment['period'], comment['text']]
            rows.append(row)
        return rows.insert(0, ['name', 'url', 'address', 'rating', 'number_of_reviews', 'comment_period', 'comment_text'])


def generate_search_url(search):
    """Generates a Google Maps search url"""
    url = "https://www.google.com/maps/search/"
    name = search.lower().strip()
    return urljoin(url, quote_plus(name))


class GoogleMapsMixin:
    def generate_csv_file(self, filename=None):
        with open('ange.json', encoding='utf-8') as f:
            data = json.load(f)

            business_comments = []
            for item in data:
                comments = item['comments']
                for comment in comments:
                    container = [
                        item['name'],
                        item['address'],
                        # item['rating'],
                        item['number_of_reviews'],
                        comment['period'],
                        comment['rating'],
                        comment['text']
                    ]
                    business_comments.append(container)
            
            with open('ange.csv', mode='w', encoding='utf-8', newline='\n') as f:
                writer = csv.writer(f)
                for row in business_comments:
                    if not row:
                        continue
                    writer.writerow(row)


class GoogleMaps(GoogleMapsMixin, SinglePageAutomater):
    final_result = []

    # start_url = "https://www.google.com/maps/search/Marie+Blach%C3%A8re/@44.2399522,1.6699718,8.75z?entry=ttu"
    # start_url = generate_search_url('la mie câline')

    def post_visit_actions(self, **kwargs):
        try:
            # Google has a special consent form
            self.driver.execute_script(
                """
                try {
                    document.querySelector('form:last-child').querySelector('button').click()
                } catch (e) {
                    // Google might have different techniques on the consent
                    // form. This is an alternative action for skipping that page
                    document.querySelector('*[aria-label="Tout accepter"]').click()
                    console.log(e)
                }
                """
            )
            time.sleep(3)
        except:
            logger.info('No consent screen')

    def run_actions(self, current_url, **kwargs):
        results_xpath = "//div[contains(@class, 'm6QErb WNBkOb')]/div[2]/div"
        results_is_scrollable = True

        scroll_script = """
            const element = document.evaluate("{results_xpath}", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null)
            const elementToScroll = element.singleNodeValue

            const elementHeight = elementToScroll.scrollHeight
            let currentPosition = elementToScroll.scrollTop

            // Indicates the scrolling speed
            const scrollStep = Math.ceil(elementHeight / 20)

            currentPosition += scrollStep
            elementToScroll.scroll(0, currentPosition)

            return [ currentPosition, elementHeight ]
        """

        saved_position = None
        scroll_script = scroll_script.format(results_xpath=results_xpath)

        while results_is_scrollable:
            result = self.driver.execute_script(scroll_script)

            current_position, element_height = result

            if self.debug_mode:
                if current_position > 500:
                    break

            if current_position >= element_height:
                results_is_scrollable = False

            # There seems to be a case where the current position
            # does not get updated and stays the same which
            # means that we have reached the bottom of the page
            if saved_position is not None and current_position == saved_position:
                results_is_scrollable = False
            saved_position = current_position
            time.sleep(2)

        businesses = []
        # 1. Get the results feed
        feed = self.driver.find_element(By.CSS_SELECTOR, 'div[role="feed"]')
        # Remove all the DIVs that do not actually have a class
        # NOTE: This is a brute force catch-all method which will
        # include DIVs that have nothing to do with the actual card
        # and can result in errors. Try-Except these.
        # items = feed.find_elements(By.CSS_SELECTOR, 'div:not([class])')
        items = feed.find_elements(By.CSS_SELECTOR, 'div[role="article"]')
        
        # Intermediate save - Saves the first initital results
        # that were found in he feed
        rows = []
        for item in items:
            try:
                link = item.find_element(By.TAG_NAME, 'a')
                name = link.get_attribute('aria-label')
                url = link.get_attribute('href')
            except:
                logger.info('Business information not found')
            else:
                rows.append([name, url])
        write_csv_document('int_save.csv', rows)

        # For each item, we need to click on the card in
        # order to get the pieces of information for the business
        items_copy = items.copy()
        comments_saved_position = None
        counter = 1
        while items_copy:
            business_information = GoogleBusiness()

            business = items_copy.pop()

            content = business.get_attribute('innerHTML')
            if content == '':
                continue

            try:
                link = business.find_element(By.TAG_NAME, 'a')
                name = link.get_attribute('aria-label')
                url = link.get_attribute('href')
                rating = business.find_element(By.CSS_SELECTOR, 'span[role="img"]').get_attribute('aria-label')
            except:
                continue
            else:
                rating, number_of_reviews = rating.split(' ')

            # Some names might contain characters such as \' which
            # can break the javascript script since there are also
            # single quotes. We need to escape those.
            javascript_business_name = ''
            if "'" in name:
                javascript_business_name = name.replace("'", "\\'")
            else:
                javascript_business_name = name

            # Opens the side panel
            link.click()
            time.sleep(2)

            # 1.1 Get additonal business information - This is
            # a brute force method that gets any business details
            # from the business information section
            business_information_script = """
            const infoSection = document.querySelector('div[class="m6QErb "][aria-label^="{business_name}"][role="region"]')
            const allDivs = infoSection.querySelectorAll('div')
            return Array.from(allDivs).map(x => x.innerText)
            """.format(business_name=javascript_business_name)
            try:
                # Some business names do not seem to be valid e.g.
                # aria-label="la mie CÂLINE - Atelier "Pains & Restauration"" which
                # breaks the script. We'll just keep going if we cannot get
                # no business information
                information = self.driver.execute_script(business_information_script)
            except Exception as e:
                counter = counter + 1
                logger.critical(f'Could not parse business information: {url}')
                continue
            else:
                clean_information = set(list(drop_null(information)))

            # 2.1. Get the side panel
            # side_panel = self.driver.find_elements(
            #     By.CSS_SELECTOR,
            #     'div[role="main"]'
            # )[-1]
            # 2.2. Move to the comment section
            tab_list = self.driver.find_elements(
                By.CSS_SELECTOR,
                '*[role="tablist"] button'
            )
            tab_list[1].click()
            time.sleep(2)

            # Scroll the comment section by using
            # the exact same above process
            comments_is_scrollable = True
            comments_scroll_script = """
                const mainWrapper = document.querySelector('div[role="main"][aria-label="{business_name}"]')
                const elementToScroll = mainWrapper.querySelector('div[tabindex="-1"]')

                const elementHeight = elementToScroll.scrollHeight
                let currentPosition = elementToScroll.scrollTop

                // Indicates the scrolling speed
                const scrollStep = Math.ceil(elementHeight / {scroll_step})

                currentPosition += scrollStep
                elementToScroll.scroll(0, currentPosition)

                return [ currentPosition, elementHeight ]
            """
            comments_scroll_script = comments_scroll_script.format(
                business_name=javascript_business_name,
                scroll_step=self.default_scroll_step
            )
            while comments_is_scrollable:
                result = self.driver.execute_script(comments_scroll_script)

                current_position, element_height = result
                if current_position >= element_height:
                    comments_is_scrollable = False

                if self.debug_mode:
                    if current_position >= 1500:
                        break

                # There seems to be a case where the current position
                # does not get updated and stays the same which
                # means that we have reached the bottom of the page
                if comments_saved_position is not None and current_position == comments_saved_position:
                    comments_is_scrollable = False
                comments_saved_position = current_position
                time.sleep(1)

            # Before retrieving all the comments
            # raise a small pause here
            time.sleep(2)

            retrieve_comments_script = """
            const commentsWrapper = document.querySelectorAll("div[data-review-id^='Ch'][class*='fontBodyMedium ']")
            
            return Array.from(commentsWrapper).map((item) => {
                let dataReviewId = item.dataset['reviewId']

                let text = ''
                let period = null
                let rating = null
                const textSection = item.querySelector("*[class='MyEned']")

                try {
                    // Sometimes there is a read more button
                    // that we have to click
                    
                    moreButton = (
                        // Try the "Voir plus" button"
                        item.querySelector('button[aria-label="Voir plus"]') ||
                        // Try the "See more" button"
                        item.querySelector('button[aria-label="See more"]') ||
                        // On last resort try "aria-expanded"
                        item.querySelector('button[aria-expanded="false"]')
                    )
                    moreButton.click()
                } catch (e) {
                    console.log('No additional data for', dataReviewId)
                }
                
                try {
                    // Or, item.querySelector('.rsqaWe').innerText
                    period = item.querySelector('.DU9Pgb').innerText
                } catch (e) {
                    // pass
                }

                try {
                    rating = item.querySelector('span[role="img"]').ariaLabel
                } catch (e) {
                    // pass
                }

                try {
                    text = textSection.innerText
                } catch (e) {
                    // pass
                }

                try {
                    reviewerName = item.querySelector('class*="d4r55"').innerText
                    reviewerNumberOfReviews = item.querySelector('*[class*="RfnDt"]').innerText
                } catch (e) {
                    // pass
                }

                return {
                    text: text,
                    rating: rating,
                    period: period
                }
            })
            """
            clean_comments = []
            try:
                comments = self.driver.execute_script(retrieve_comments_script)
            except Exception as e:
                comments = ''
                logger.error(f'Comments not found for {name}: {e.args}')
            else:
                comments = list(drop_null((comments)))
                for comment in comments:
                    if not isinstance(comment, dict):
                        continue
                    
                    clean_dict = {}
                    for key, value in comment.items():
                        clean_text = self.clean_text(value) 
                        clean_dict[key] = clean_text
                    clean_comments.append(clean_dict)
                logger.info(f'Found {len(clean_comments)} reviews')

            def clean_information_list(items):
                # Remove useless data from the array
                # of values that we have received
                exclude = ['lundi', 'mardi', 'mercredi', 'jeudi',
                            'vendredi', 'samedi', 'dimanche']
                result1 = []
                for text in items:
                    if text in exclude:
                        continue
                    result1.append(text)

                result2 = []
                for text in result1:
                    logic = [
                        'Commander' in text,
                        'ubereats.com' in text,
                        text.startswith('lundi'),
                        text.startswith('mardi'),
                        text.startswith('mercredi'),
                        text.startswith('jeudi'),
                        text.startswith('vendredi'),
                        text.startswith('samedi'),
                        text.startswith('dimanche'),
                        text.startswith('Ouvert'),
                        text.startswith('Envoyer vers'),
                        text.startswith('Suggérer'),
                        text.startswith('Revendiquer cet')
                    ]
                    if any(logic):
                        continue
                    result2.append(text)
                return result2


            business_information.name = name
            business_information.url = url
            business_information.address = clean_information_list(
                list(clean_information)
            )
            business_information.rating = rating
            business_information.number_of_reviews = number_of_reviews
            business_information.comments = clean_comments
            businesses.append(business_information)
            self.final_result = businesses

            logger.info(f'Completed {counter} of {len(items)} business cards')
            counter = counter + 1
            time.sleep(2)

        data = list(map(lambda x: x.as_json, businesses))
        filename = self.get_filename(extension='json')
        write_json_document(filename, data)
        logger.info(f'File created: {filename}')


class GoogleMapsPlace(GoogleMaps):
    def run_actions(self, current_url, **kwargs):
        current_time = time.time()
        business_information = GoogleBusiness()

        try:
            name = self.driver.find_element(By.CSS_SELECTOR, 'h1.DUwDvf.fontHeadlineLarge').text
            url = self.driver.current_url
            rating_section = self.driver.find_element(By.CSS_SELECTOR, '.F7nice')
            rating, number_of_reviews = rating_section.text.split('\n')
        except:
            name = None
            url = self.driver.current_url
            rating = None
            number_of_reviews = None
        else:
            number_of_reviews = number_of_reviews.replace('(', '')
            number_of_reviews = number_of_reviews.replace(')', '')

        # If we were not able to get a
        # name, come from the principle
        # that the page was not found
        if name is None:
            return False

        # Some names might contain characters such as \' which
        # can break the javascript script since there are also
        # single quotes. We need to escape those.
        javascript_business_name = ''
        if "'" in name:
            javascript_business_name = name.replace("'", "\\'")
        else:
            javascript_business_name = name

        time.sleep(2)

        # 1.1 Get additonal business information - This is
        # a brute force method that gets any business details
        # from the business information section
        business_information_script = """
        const infoSection = document.querySelector('div[class="m6QErb "][aria-label^="{business_name}"][role="region"]')
        const allDivs = infoSection.querySelectorAll('div')
        return Array.from(allDivs).map(x => x.innerText)
        """.format(business_name=javascript_business_name)
        try:
            # Some business names do not seem to be valid e.g.
            # aria-label="la mie CÂLINE - Atelier "Pains & Restauration"" which
            # breaks the script. We'll just keep going if we cannot get
            # no business information
            information = self.driver.execute_script(
                business_information_script)
        except Exception as e:
            logger.critical(f'Could not parse business information: {url}')
            return False
        else:
            clean_information = set(list(drop_null(information)))

        # 2.2. Move to the comment section
        tab_list = self.driver.find_elements(
            By.CSS_SELECTOR,
            '*[role="tablist"] button'
        )
        tab_list[1].click()
        time.sleep(2)

        # Scroll the comment section by using
        # the exact same above process
        comments_is_scrollable = True
        comments_scroll_script = """
            const mainWrapper = document.querySelector('div[role="main"][aria-label="{business_name}"]')
            const elementToScroll = mainWrapper.querySelector('div[tabindex="-1"]')

            const elementHeight = elementToScroll.scrollHeight
            let currentPosition = elementToScroll.scrollTop

            // Indicates the scrolling speed
            const scrollStep = Math.ceil(elementHeight / {scroll_step})

            currentPosition += scrollStep
            elementToScroll.scroll(0, currentPosition)

            return [ currentPosition, elementHeight ]
        """
        comments_scroll_script = comments_scroll_script.format(
            business_name=javascript_business_name,
            scroll_step=self.default_scroll_step
        )

        comments_saved_position = None
        while comments_is_scrollable:
            result = self.driver.execute_script(comments_scroll_script)

            current_position, element_height = result
            if current_position >= element_height:
                comments_is_scrollable = False

            if self.debug_mode:
                if current_position >= 1500:
                    break

            # There seems to be a case where the current position
            # does not get updated and stays the same which
            # means that we have reached the bottom of the page
            if comments_saved_position is not None and current_position == comments_saved_position:
                comments_is_scrollable = False
            comments_saved_position = current_position
            time.sleep(1)

        # Before retrieving all the comments
        # raise a small pause here
        time.sleep(2)

        retrieve_comments_script = """
        const commentsWrapper = document.querySelectorAll("div[data-review-id^='Ch'][class*='fontBodyMedium ']")
        
        return Array.from(commentsWrapper).map((item) => {
            let dataReviewId = item.dataset['reviewId']

            let text = ''
            let period = null
            let rating = null
            const textSection = item.querySelector("*[class='MyEned']")

            try {
                // Sometimes there is a read more button
                // that we have to click
                
                moreButton = (
                    // Try the "Voir plus" button"
                    item.querySelector('button[aria-label="Voir plus"]') ||
                    // Try the "See more" button"
                    item.querySelector('button[aria-label="See more"]') ||
                    // On last resort try "aria-expanded"
                    item.querySelector('button[aria-expanded="false"]')
                )
                moreButton.click()
            } catch (e) {
                console.log('No additional data for', dataReviewId)
            }
            
            try {
                // Or, item.querySelector('.rsqaWe').innerText
                period = item.querySelector('.DU9Pgb').innerText
            } catch (e) {
                // pass
            }

            try {
                rating = item.querySelector('span[role="img"]').ariaLabel
            } catch (e) {
                // pass
            }

            try {
                text = textSection.innerText
            } catch (e) {
                // pass
            }

            try {
                reviewerName = item.querySelector('class*="d4r55"').innerText
                reviewerNumberOfReviews = item.querySelector('*[class*="RfnDt"]').innerText
            } catch (e) {
                // pass
            }

            return {
                text: text,
                rating: rating,
                period: period
            }
        })
        """
        clean_comments = []
        try:
            comments = self.driver.execute_script(retrieve_comments_script)
        except Exception as e:
            comments = ''
            logger.error(f'Comments not found for {name}: {e.args}')
        else:
            comments = list(drop_null((comments)))
            for comment in comments:
                if not isinstance(comment, dict):
                    continue

                clean_dict = {}
                for key, value in comment.items():
                    clean_text = self.clean_text(value)
                    clean_dict[key] = clean_text
                clean_comments.append(clean_dict)
            logger.info(f'Found {len(clean_comments)} reviews')

        def clean_information_list(items):
            # Remove useless data from the array
            # of values that we have received
            exclude = ['lundi', 'mardi', 'mercredi', 'jeudi',
                        'vendredi', 'samedi', 'dimanche']
            result1 = []
            for text in items:
                if text in exclude:
                    continue
                result1.append(text)

            result2 = []
            for text in result1:
                logic = [
                    'Commander' in text,
                    'ubereats.com' in text,
                    text.startswith('lundi'),
                    text.startswith('mardi'),
                    text.startswith('mercredi'),
                    text.startswith('jeudi'),
                    text.startswith('vendredi'),
                    text.startswith('samedi'),
                    text.startswith('dimanche'),
                    text.startswith('Ouvert'),
                    text.startswith('Envoyer vers'),
                    text.startswith('Suggérer'),
                    text.startswith('Trouver'),
                    text.startswith('Revendiquer cet')
                ]
                if any(logic):
                    continue
                result2.append(text)
            return result2

        business_information.name = name
        business_information.url = url
        business_information.address = clean_information_list(
            list(clean_information)
        )
        business_information.rating = rating
        business_information.number_of_reviews = number_of_reviews
        business_information.comments = clean_comments
        self.final_result.append(business_information)

        time.sleep(2)

        data = list(map(lambda x: x.as_json, self.final_result))
        write_json_document('ssr.json', data)
        # completion_time = (time.time() - current_time) / 60


if __name__ == '__main__':
    # try:
    #     instance = GoogleMapsPlace()
    #     # instance = GoogleMaps()
    #     urls = [
    #         'https://www.google.fr/maps/place/Bricomarch%C3%A9/@45.0623843,5.0824153,13z/data=!4m10!1m2!2m1!1sbricomarch%C3%A9!3m6!1s0x478ab2c99e97aba7:0xf9a321930a23c394!8m2!3d45.05827!4d5.107725!15sCgxicmljb21hcmNow6kiA4gBAZIBFGRvX2l0X3lvdXJzZWxmX3N0b3Jl4AEA!16s%2Fg%2F1w8w8xmm?entry=ttu'
    #     ]
    #     instance.start(start_urls=urls, wait_time=1)
    # except KeyboardInterrupt:
    #     data = list(map(lambda x: x.as_json, instance.final_result))
    #     write_json_document('dump.json', data)
    #     logger.critical(f"Dumping data to 'dump.json'")
    # except Exception:
    #     data = list(map(lambda x: x.as_json, instance.final_result))
    #     write_json_document('dump.json', data)
    #     logger.critical(f"Dumping data to 'dump.json'")
    #     raise

    instance = GoogleMapsPlace()
    url_file = URLFile(processor=generate_search_url)
    instance.start(start_urls=list(url_file))
