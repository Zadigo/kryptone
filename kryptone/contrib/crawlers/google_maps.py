import csv
import json
import time
from urllib.parse import quote_plus, urljoin

from selenium.webdriver.common.by import By

from kryptone import logger
from kryptone.base import SiteCrawler
from kryptone.contrib.models import GoogleBusiness
from kryptone.utils.file_readers import write_csv_document, write_json_document
from kryptone.utils.iterators import drop_null
from kryptone.utils.text import create_filename


def generate_search_url(search):
    """Generates a Google Maps search url"""
    url = "https://www.google.com/maps/search/"
    name = search.lower().strip()
    return urljoin(url, quote_plus(name))


class GoogleMapsMixin:
    return_comments = True

    class Meta:
        crawl = False
    
    @staticmethod
    def transform_to_json(items):
        return list(map(lambda x: x.as_json(), items))

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


class GoogleMaps(GoogleMapsMixin, SiteCrawler):
    """Explores the business feed, gathers each business
    and returns the data"""

    final_result = []

    def create_dump(self):
        write_json_document(
            'dump.json', self.transform_to_json(self.final_result))

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

            if self._meta.debug_mode:
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
        if not items:
            # Try an alternative method which consists of
            # getting the DIVs with no class and then
            # performing the rest of the actions on them
            items = feed.find_elements(
                By.CSS_SELECTOR,
                'div[role="feed"] div:not([class])'
            )

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
        write_csv_document('business_urls_save.csv', rows)

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
                rating = business.find_element(
                    By.CSS_SELECTOR, 'span[role="img"]').get_attribute('aria-label')
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
            try:
                link.click()
            except:
                continue
            else:
                # Since the url is dynamic we have to query the driver
                # to get the current displayed url. This technique is
                # used as it is way more easier than right clicking
                # to get the coordinates
                feed_url_script = """return document.location.href"""
                feed_url = self.driver.execute_script(feed_url_script)
                business_information.feed_url = feed_url
                business_information.get_gps_coordinates_from_url()
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
                    business_information_script
                )
            except Exception as e:
                counter = counter + 1
                logger.critical(f'Could not parse business information: {url}')
                continue
            else:
                clean_information = set(list(drop_null(information)))

            if self.return_comments:
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
                try:
                    tab_list[1].click()
                except:
                    continue
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

                    if self._meta.debug_mode:
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
                            cleaned_text = clean_text(value)
                            clean_dict[key] = cleaned_text
                        clean_comments.append(clean_dict)
                    business_information.comments = clean_comments
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
            businesses.append(business_information)
            self.final_result = businesses

            logger.info(f'Completed {counter} of {len(items)} business cards')
            counter = counter + 1
            time.sleep(2)

        data = list(map(lambda x: x.as_json(), businesses))
        filename = create_filename()
        write_json_document(filename, data)
        logger.info(f'File created: {filename}')


class GoogleMapsPlace(GoogleMaps):
    """Gathers data for a Google Business place"""

    def run_actions(self, current_url, **kwargs):
        current_time = time.time()
        business_information = GoogleBusiness()

        try:
            name = self.driver.find_element(
                By.CSS_SELECTOR, 'h1.DUwDvf.fontHeadlineLarge'
            ).text
            url = self.driver.current_url
            rating_section = self.driver.find_element(
                By.CSS_SELECTOR, '.F7nice')
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
                business_information_script
            )
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
        try:
            tab_list[1].click()
        except:
            return False
        time.sleep(2)

        if self.return_comments:
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
                        cleaned_text = clean_text(value)
                        clean_dict[key] = cleaned_text
                    clean_comments.append(clean_dict)
                logger.info(f'Found {len(clean_comments)} reviews')

            # Save the comments on the model
            business_information.comments = clean_comments

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
        self.final_result.append(business_information)

        time.sleep(2)

        data = list(map(lambda x: x.as_json, self.final_result))
        write_json_document('google_maps_results.json', data)
        # completion_time = (time.time() - current_time) / 60
