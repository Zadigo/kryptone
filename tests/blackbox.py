"""
This is a blackbox used to the test the
integrity of the crawler classes
"""

from selenium.webdriver.common.by import By

from kryptone.base import BaseCrawler
from kryptone.utils.file_readers import write_json_document
from kryptone.utils.text import parse_price


class Etam(BaseCrawler):
    start_url = 'https://www.etam.com/culottes-et-bas-tangas/'
    browser_name = 'Edge'

    def post_visit_actions(self, **kwargs):
        self.click_consent_button(element_id='acceptAllCookies')

    def run_actions(self, current_url, **kwargs):
        self.save_to_local_storage('url', current_url)


if __name__ == '__main__':
    instance = Etam()
    instance.start(wait_time=10)


# if __name__ == '__main__':
#     # try:
#     #     instance = GoogleMapsPlace()
#     #     # instance = GoogleMaps()
#     #     urls = [
#     #         'https://www.google.fr/maps/place/Bricomarch%C3%A9/@45.0623843,5.0824153,13z/data=!4m10!1m2!2m1!1sbricomarch%C3%A9!3m6!1s0x478ab2c99e97aba7:0xf9a321930a23c394!8m2!3d45.05827!4d5.107725!15sCgxicmljb21hcmNow6kiA4gBAZIBFGRvX2l0X3lvdXJzZWxmX3N0b3Jl4AEA!16s%2Fg%2F1w8w8xmm?entry=ttu'
#     #     ]
#     #     instance.start(start_urls=urls, wait_time=1)
#     # except KeyboardInterrupt:
#     #     data = list(map(lambda x: x.as_json, instance.final_result))
#     #     write_json_document('dump.json', data)
#     #     logger.critical(f"Dumping data to 'dump.json'")
#     # except Exception:
#     #     data = list(map(lambda x: x.as_json, instance.final_result))
#     #     write_json_document('dump.json', data)
#     #     logger.critical(f"Dumping data to 'dump.json'")
#     #     raise

#     instance = GoogleMapsPlace()
#     url_file = URLFile(processor=generate_search_url)
#     instance.start(start_urls=list(url_file))
