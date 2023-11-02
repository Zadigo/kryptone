from kryptone import logger
from kryptone.base import SiteCrawler
from kryptone.mixins import SEOMixin
from kryptone.utils import file_readers


class SEOCrawler(SiteCrawler, SEOMixin):
    def resume(self, **kwargs):
        data = file_readers.read_json_document('cache.json')

        # Before reloading the urls, run the filters
        # in case previous urls to exclude were
        # present
        valid_urls = self.url_filters(data['urls_to_visit'])
        self.urls_to_visit = set(valid_urls)
        self.visited_urls = set(data['visited_urls'])

        previous_seen_urls = file_readers.read_csv_document('seen_urls.csv', flatten=True)
        self.list_of_seen_urls = set(previous_seen_urls)

        self.page_audits = file_readers.read_json_document('audit.json')
        self.text_by_page = file_readers.read_json_document('text_by_pages.json')

        self.start(**kwargs)
    
    def run_actions(self, current_url, **kwargs):
        self.audit_page(current_url)
        file_readers.write_json_document('audit.json', self.page_audits)

        # Write vocabulary as JSON
        vocabulary = self.global_audit()
        file_readers.write_json_document('global_audit.json', vocabulary)

        # Write vocabulary as CSV
        rows = []
        for key, value in vocabulary.items():
            rows.append([key, value])
        file_readers.write_csv_document('global_audit.csv', rows)

        # Save the website's text
        website_text = ' '.join(self.fitted_page_documents)
        file_readers.write_text_document(
            'website_text.txt', 
            website_text
        )

        file_readers.write_json_document(
            'text_by_pages.json',
            self.text_by_page
        )
        
        # db_signal.send(
        #     self,
        #     page_audit=self.page_audits,
        #     global_audit=vocabulary
        # )

        logger.info(f'Audit complete for {str(current_url)}')
