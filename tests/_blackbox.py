from kryptone.app import BaseCrawler

class ForTesting(BaseCrawler):
    start_url = 'https://www.jennyfer.com/fr-fr/vetements/maillots-de-bain/'


if __name__ == '__main__':
    testing = ForTesting()
    testing.start()
