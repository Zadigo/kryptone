import asyncio

from kryptone import logger
from kryptone.mixins import SEOMixin
from kryptone.utils import file_readers

# TODO: Reunite these two classes


class SEOCrawler(SEOMixin):
    """A crawler specialized for running
    SEO tasks on a given website"""

    def resume(self, **kwargs):
        data = file_readers.read_json_document('cache.json')

        # Before reloading the urls, run the filters
        # in case previous urls to exclude were
        # present
        valid_urls = self.url_filters(data['urls_to_visit'])
        self.urls_to_visit = set(valid_urls)
        self.visited_urls = set(data['visited_urls'])

        previous_seen_urls = file_readers.read_csv_document(
            'seen_urls.csv',
            flatten=True
        )
        self.list_of_seen_urls = set(previous_seen_urls)

        self.page_audits = file_readers.read_json_document('audit.json')
        self.text_by_page = file_readers.read_json_document(
            'text_by_pages.json')

        self.start(**kwargs)

    def current_page_actions(self, current_url, **kwargs):
        self.audit_page(current_url)

        async def write_audit_documents():
            file_readers.write_json_document(
                'word_frequency.json', 
                self.word_frequency_by_page
            )
            file_readers.write_json_document('audit.json', self.page_audits)

        async def write_vocabulary():
            # Write vocabulary as CSV
            rows = []
            for word, value in self.website_word_frequency.items():
                rows.append([word, value])
            file_readers.write_csv_document('word_count.csv', rows)

        async def write_website_text():
            # Save the website's text
            website_text = ''.join(self.fitted_page_documents)
            file_readers.write_text_document(
                'website_text.txt',
                website_text
            )

            file_readers.write_json_document(
                'text_by_pages.json',
                self.text_by_page
            )

            file_readers.write_json_document(
                'website_tokens.json',
                list(self.website_tokens)
            )

            file_readers.write_json_document(
                'stemmed_words.json',
                list(self.stemmed_tokens)
            )

        async def main():
            task1 = asyncio.create_task(write_audit_documents())
            task2 = asyncio.create_task(write_vocabulary())
            task3 = asyncio.create_task(write_website_text())
            tasks = [task1, task2, task3]

            for coroutine in asyncio.as_completed(tasks):
                await coroutine

        asyncio.run(main())

        # db_signal.send(
        #     self,
        #     page_audit=self.page_audits,
        #     global_audit=vocabulary
        # )

        logger.info(f'Audit complete for {str(current_url)}')
