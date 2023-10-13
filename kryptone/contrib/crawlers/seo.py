from kryptone.base import SiteCrawler
from kryptone.utils import file_readers
from kryptone import logger
from kryptone.mixins import SEOMixin


class SEOCrawler(SiteCrawler, SEOMixin):
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
            'website_text.txt', website_text)

        # db_signal.send(
        #     self,
        #     page_audit=self.page_audits,
        #     global_audit=vocabulary
        # )

        logger.info('Audit complete...')
