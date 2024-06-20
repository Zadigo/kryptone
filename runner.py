from kryptone.base import SiteCrawler
from kryptone.utils.urls import URLIgnoreTest

IGNORE_URLS = [
    'faq-faq',
    'shipup',
    'carte-cadeau',
    'culottes-et-bas-guide-accueil',
    'guide-des-tailles',
    'guide-des-tailles-sizeguide.html',
    'carte-cadeaux',
    'new-pleazpay.html',
    'paiement-en-3-fois-avec-scalapay-scalapay.html',
    'jobs',
    'cart',
    'account',
    'faq-section',
    'no-name-garantiesetservices.html',
    'livraisons-et-retours-livraisonsretours.html',
    'mentions-legales-conditions-generales',
    'charte-d-utilisation-des-cookies-chartecookiergpd',
    'conditions-de-l-offre-offerconditions.html',
    'magasins'
]


class TestCrawler(SiteCrawler):
    start_url = 'https://www.jennyfer.com/fr-fr/vetements/maillots-de-bain/haut-de-maillot-de-bain/haut-de-maillot-de-bain-crepe-noir-10040867060.html'

    class Meta:
        crawl = True
        url_ignore_tests = [
            URLIgnoreTest(
                'base_pages',
                paths=IGNORE_URLS
            )
        ]
        url_rule_tests = [
            r'\/vetements\/'
        ]


t = TestCrawler(browser_name='Edge')
t.start()
# t.boost_start(windows=3)
