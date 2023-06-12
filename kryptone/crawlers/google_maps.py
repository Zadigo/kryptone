import dataclasses
import random
import re
import time

from jennyfer.models import GoogleBusiness
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from kryptone.app import BaseCrawler
from kryptone.utils.file_readers import write_json_document
from kryptone.utils.iterators import drop_null
from kryptone.utils.text import clean_text, parse_price


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


class GoogleMaps(BaseCrawler):
    # start_url = 'https://www.google.com/maps/search/sophie+lebreuilly/@50.6472975,2.8742715,10z/data=!3m1!4b1?entry=ttu'
    start_url = 'https://www.google.com/maps/search/la+paneti%C3%A8re/@47.0380946,-1.5755537,6z/data=!3m1!4b1?entry=ttu'
    final_result = []

    def run_actions(self, current_url, **kwargs):
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
            pass

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
        # For each item, we need to click on the card in
        # order to get the pieces of information for the business
        items_copy = items.copy()
        comments_saved_position = None
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

            # try:
            #     data = business.find_element(By.CSS_SELECTOR, 'span[role="img"]')
            # except:
            #     rating = None
            #     reviews = None
            # else:
            #     has_match = re.match(r'\d+\.?\d+', data).group(0)
            #     rating = has_match.group(1) if has_match else None
            #     reviews = data.split('(')[-1].replace(')', '')

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
            """.format(business_name=name)
            information = self.driver.execute_script(business_information_script)
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
                const scrollStep = Math.ceil(elementHeight / 10)

                currentPosition += scrollStep
                elementToScroll.scroll(0, currentPosition)

                return [ currentPosition, elementHeight ]
            """
            comments_scroll_script = comments_scroll_script.format(
                business_name=name
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

            retrieve_comments_script = """
            // const xpath = "//div[starts-with(@data-review-id, 'Ch')][contains(@class, 'fontBodyMedium')]//*[@class='MyEned']"
            // const text = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue

            const commentsWrapper = document.querySelectorAll("div[data-review-id^='Ch'][class*='fontBodyMedium']")
            
            return Array.from(commentsWrapper).map((commentWrapper) => {
                const textSection = commentWrapper.querySelector("*[class='MyEned']")

                // Sometimes there is a read more button
                // that we have to click
                try {
                    textSection.querySelector('button[aria-label="Voir plus"]').click()
                } catch (e) {
                    console.log(e)
                }
                
                try {
                    period = commentWrapper.querySelector('.DU9Pgb').innerText
                } catch (e) {
                    // pass
                }

                return {
                    text: textSection.innerText,
                    period: period
                }
            })
            """
            try:
                comments = self.driver.execute_script(retrieve_comments_script)
            except:
                comments = ''
            else:
                comments = list(drop_null((comments)))
                clean_comments = []
                for comment in comments:
                    if not isinstance(comment, dict):
                        continue
                    
                    clean_dict = {}
                    for key, value in comment.items():
                        clean_text = self.clean_text(value) 
                        clean_dict[key] = clean_text
                    clean_comments.append(clean_dict)

            def clean_information_list(items):
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
                        text.startswith('lundi'),
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
            time.sleep(2)

        data = list(map(lambda x: x.as_json, businesses))
        write_json_document('test_maps.json', data)


if __name__ == '__main__':
    try:
        instance = GoogleMaps()
        instance.start(crawl=False, debug_mode=True, wait_time=1)
    except KeyboardInterrupt:
        data = list(map(lambda x: x.as_json, instance.final_result))
        write_json_document('test_maps.json', data)
    except Exception:
        data = list(map(lambda x: x.as_json, instance.final_result))
        write_json_document('test_maps.json', data)

