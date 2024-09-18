# import dataclasses
# from kryptone._new_base import SiteCrawler


# @dataclasses.dataclass
# class CustomData:
#     title: str


# class CustomSpider(SiteCrawler):
#     model = CustomData

#     class Meta:
#         debug_mode = False

#     def backup_urls(self):
#         return super().backup_urls()

#     def current_page_actions(self, current_url, **kwargs):
#         product_title = self.driver.execute_script("""
#         const el = document.querySelector('h1.productTitle__name')
#         return { title: el?.textContent }""")
#         print(product_title)
#         self.save_object(product_title, check_fields_null=['title'])


# c = CustomSpider(browser_name='Edge')
# c.start_url = 'https://www.etam.com/c/lingerie/'
# print(c.start())
