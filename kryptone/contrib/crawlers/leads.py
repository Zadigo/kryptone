from kryptone import logger
from kryptone.base import SiteCrawler
from kryptone.mixins import EmailMixin
from kryptone.utils import file_readers


class LeadsCrawler(EmailMixin):
    """A crawler specialize in finding emails on a website"""

    def current_page_actions(self, current_url, **kwargs):
        self.emails(
            self.get_page_text,
            elements=self.get_page_link_elements
        )
        # Format each email as [[...], ...] in order to comply
        # with the way that the csv writer outputs the rows
        emails = list(map(lambda x: [x], self.emails_container))
        file_readers.write_csv_document('emails.csv', emails)
        # db_signal.send(
        #     self,
        #     emails=self.emails_container
        # )
