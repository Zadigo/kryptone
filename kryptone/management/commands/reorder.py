import kryptone
import re
from kryptone import logger
from kryptone.management.base import ProjectCommand
from kryptone.checks.core import checks_registry
import pandas
from kryptone.utils.file_readers import read_json_document, write_json_document


class Command(ProjectCommand):
    requires_system_checks = True

    def add_arguments(self, parser):
        parser.add_argument(
            'regex_pattern',
            type=str,
            help='Regex pattern to identify the urls that match'
        )

    def execute(self, namespace):
        kryptone.setup()
        checks_registry.run()

        data = read_json_document('cache.json')
        urls_to_visit = data['urls_to_visit']

        df = pandas.DataFrame({'urls': urls_to_visit})

        def match_regex(url):
            result = re.search(namespace.regex_pattern, url)
            if result:
                return True
            return False
        
        df['has_match'] = df['urls'].map(match_regex)

        valid_urls = df[df['has_match'] == True]
        invalid_urls = df[df['has_match'] == False]

        valid_urls_list = valid_urls['urls'].values.tolist()
        invalid_urls_list = invalid_urls['urls'].values.tolist()
        valid_urls_list.extend(invalid_urls)

        data['urls_to_visit'] = valid_urls_list

        if valid_urls_list or invalid_urls_list:
            write_json_document('cache.json', data)
        logger.info(
            f"The urls were reordered sucessfully "
            "using: {namespace.regex_pattern}"
        )
