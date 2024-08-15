import re
import pathlib
from kryptone.conf import settings
from kryptone.management.base import BaseCommand


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            'project',
            help='Project name',
            type=str
        )

    def normalize_file_name(self, path):
        path_name = path.stem
        if path_name.endswith('_tpl'):
            true_name = path_name.removesuffix('_tpl')
            return f'{true_name}.py'
        return path_name

    def create_new_file(self, source, destination, project_name=None):
        with open(source, mode='rb') as f:
            content = f.read().decode('utf-8')
            base_name = self.normalize_file_name(source)
            file_to_create = destination / base_name

            if base_name == 'manage.py':
                content = re.sub(
                    r'(project_name_placeholder)',
                    project_name,
                    content
                )

            # if base_name == 'settings.py':
            #     content = re.sub(
            #         r'PROJECT\_PATH\s\=\sNone',
            #         'PROJECT_PATH = pathlib.Path(__file__).parent.absolute()',
            #         content
            #     )

            with open(file_to_create, mode='wb') as d:
                d.write(content.encode('utf-8'))

    def execute(self, namespace):
        project_name = namespace.project
        if project_name is None:
            raise ValueError('You should provide a name for your project')

        current_directory = pathlib.Path.cwd()
        project_path = current_directory / project_name

        if project_path.exists():
            raise ValueError('Project already exists')
        project_path.mkdir()

        # The folder that contains the templates that
        # we need to copy to the local project
        templates_directory = settings.GLOBAL_KRYPTONE_PATH / 'templates'
        list_of_template_files = list(templates_directory.glob('*'))

        # 1. Create the directories
        for path in list_of_template_files:
            if not path.is_dir():
                continue
            directory_to_create = project_path / path.name
            directory_to_create.mkdir()

        # 2. Create the root file elements
        for path in list_of_template_files:
            if not path.is_file():
                continue
            self.create_new_file(path, project_path, project_name=project_name)
