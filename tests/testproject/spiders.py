import re
import time

from selenium.webdriver.common.by import By
from kryptone.utils.urls import URLPassesTest

from kryptone.base import SiteCrawler
from kryptone.contrib.crawlers.ecommerce import EcommerceCrawlerMixin

IGNORE_URLS = [
    'faq-faq',
    'shipup',
    'carte-cadeau',
    'culottes-et-bas-guide-accueil',
    'guide-des-tailles-sizeguide.html',
    'carte-cadeaux',
    'new-pleazpay.html',
    'paiement-en-3-fois-avec-scalapay-scalapay.html',
    'jobs',
    'cart',
    'accounts',
    'faq-section',
    'no-name-garantiesetservices.html',
    'livraisons-et-retours-livraisonsretours.html',
    'mentions-legales-conditions-generales',
    'charte-d-utilisation-des-cookies-chartecookiergpd',
    'conditions-de-l-offre-offerconditions.html',
    'magasins'
]


class Jennyfer(EcommerceCrawlerMixin, SiteCrawler):
    # start_url = 'https://www.jennyfer.com/fr-fr/vetements/maillots-de-bain/'
    start_url = 'https://www.jennyfer.com/fr-fr/vetements/maillots-de-bain/haut-de-maillot-de-bain/haut-de-maillot-de-bain-crepe-noir-10040867060.html'

    class Meta:
        url_passes_tests = [
            URLPassesTest(
                'base_pages',
                paths=IGNORE_URLS
            )
        ]

    def create_dump(self):
        print('Dumping data')

    def post_visit_actions(self, **kwargs):
        time.sleep(2)
        self.click_consent_button(element_id='onetrust-accept-btn-handler')

        # try:
        #     download_app_button = self.driver.find_element(
        #         By.CSS_SELECTOR,
        #         'svg[class="qlf-close-button__svg"]'
        #     )
        #     download_app_button.click()
        # except:
        #     pass

    def run_actions(self, current_url, **kwargs):
        print(current_url)
        self.scroll_window(stop_at=5000)
