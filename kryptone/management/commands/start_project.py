import os
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

    # @staticmethod
    # def _transform_file_name(name_or_path):
    #     """Transforms a _tpl file to Python module"""
    #     if name_or_path.endswith('tpl'):
    #         name_or_path = name_or_path.removesuffix('_tpl')
    #     return f'{os.path.basename(name_or_path)}.py'

    # def _create_new_file(self, source, destination, **kwargs):
    #     """Helper for creating a new file in a local
    #     project folder"""
    #     with open(source, mode='rb') as f:
    #         base_name = self._transform_file_name(source)

    #         file_to_create = os.path.join(destination, base_name)
    #         content = f.read().decode('utf-8')

    #         if base_name == 'manage.py':
    #             project_name = kwargs.get('project_name', None)
    #             content = re.sub(
    #                 r'(project_name_placeholder)',
    #                 project_name,
    #                 content
    #             )

    #         with open(file_to_create, mode='wb') as d:
    #             d.write(content.encode('utf-8'))

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

        # 3. Create the sub files elements

        # # Construct a full path to the
        # # project's root directory
        # current_dir = os.path.abspath(os.curdir)
        # full_project_path_dir = os.path.join(current_dir, project_name)

        # zineb_templates_dir_path = os.path.join(
        #     settings.GLOBAL_KRYPTONE_PATH,
        #     'templates'
        # )
        # zineb_template_items = list(os.walk(zineb_templates_dir_path))
        # # Get the list that references the folders in the
        # # templates directory
        # root_path, folders, root_files = zineb_template_items.pop(0)
        # # Create the base folders
        # for folder in folders:
        #     os.makedirs(os.path.join(full_project_path_dir, folder))

        # for file in root_files:
        #     self._create_new_file(
        #         os.path.join(root_path, file),
        #         full_project_path_dir,
        #         project_name=project_name
        #     )

        # # Now once the main root elements were
        # # created, create the sub elements
        # for items in zineb_template_items:
        #     full_path, folder, files = items
        #     for file in files:
        #         self._create_new_file(
        #             os.path.join(full_path, file),
        #             os.path.join(
        #                 full_project_path_dir,
        #                 os.path.basename(full_path)
        #             )
        #         )
