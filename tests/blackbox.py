# from kryptone.base import SiteCrawler
# from kryptone.utils.urls import URLPassesTest
# from kryptone.contrib.crawlers.ecommerce import EcommerceCrawlerMixin

# class TestSomething(EcommerceCrawlerMixin, SiteCrawler):
#     start_url = 'https://www.etam.com/culottes-et-bas-strings/string-en-microfibre-et-dentelle-653945770.html'

#     class Meta:
#         audit_page = False
#         debug_mode = True
#         gather_emails = False
#         site_language = 'fr'
#         url_passes_tests = [
#             URLPassesTest(
#                 'base_pages',
#                 paths=[
#                     'cgv.html',
#                     'carte-cadeau/'
#                 ]
#             )
#         ]

#     def post_visit_actions(self, **kwargs):
#         self.click_consent_button(element_id='acceptAllCookies')

#     def run_actions(self, current_url, **kwargs):
#         regex = '\/?[a-z\-]+\/[a-z\-]+\-\d+\.html$'
#         if current_url.test_path(regex):
#             pass


# if __name__ == '__main__':
#     t = TestSomething(browser_name='Edge')
#     # t.start()
#     t.start()
