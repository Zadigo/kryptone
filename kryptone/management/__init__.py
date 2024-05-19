import os
from collections import OrderedDict
from importlib import import_module
from os.path import basename

# NOTE: In order for certain commands to work when
# testing ex. startproject myproject, in order for
# the second command to work correctly, its better
# to call a file with the vscode debugger and the
# arguments that we want. Otherwise, for whatever
# reason there is an error on the second command.


def collect_commands():
    """
    This collects all the paths to the commands
    located in the `management/commands` directory
    without loading any of them
    """
    from kryptone.conf import settings
    path = os.path.join(
        settings.GLOBAL_KRYPTONE_PATH,
        'management',
        'commands'
    )
    if not os.path.exists(path):
        raise FileExistsError(f'Path for commmands is not valid: {path}')

    commands_path = list(os.walk(path))
    files = commands_path[0][-1]
    complete_paths = map(lambda filename: os.path.join(
        commands_path[0][0], filename), files)
    return complete_paths


def load_command_class(name):
    """
    Loads each commands in the `management/commands` directory
    and then returns the Command class instance of a specific
    command specified the name in the parameter
    """
    paths = collect_commands()
    for path in paths:
        module_name = basename(path)
        name, _ = module_name.split('.')
        try:
            module = import_module(f'kryptone.management.commands.{name}')
        except:
            raise ImportError(
                f"Could not import module at {path} from the Kryptone commands directory.")
        return module.Command()


class Utility:
    """
    This is the main class that encapsulates the logic
    for creating and using the command parser
    """
    commands_registry = OrderedDict()

    def __init__(self):
        modules_paths = collect_commands()

        for path in modules_paths:
            module_name = basename(path)
            true_name, _ = module_name.split('.')
            try:
                module_obj = import_module(
                    f'kryptone.management.commands.{true_name}')
            except Exception as e:
                raise ImportError(
                    "Could not import module "
                    f"at {path}. {e.args[0]}"
                )
            self.commands_registry[true_name] = module_obj.Command()

    def _parse_incoming_commands(self, args: list):
        if len(args) <= 1:
            message = (
                'You called manage.py or python -m kryptone '
                'without specifying a commands to run.'
            )
            raise ValueError(message)
        name = args[0]
        remaining_tokens = args[1:]
        return name, remaining_tokens

    def _find_similar_command(self, name):
        command_names = self.commands_registry.keys()
        commands = list(filter(lambda x: name in x, command_names))
        return ' or '.join(commands)

    def call_command(self, name: list):
        """
        Call a specific command from the registry
        """
        module_or_file, tokens = self._parse_incoming_commands(name)
        command_name = tokens.pop(0)
        command_instance = self.commands_registry.get(command_name, None)
        if command_instance is None:
            message = (
                f"Command '{command_name}' does not exist. "
                f"Did you mean {self._find_similar_command(command_name)}?"
            )
            raise ValueError(message)

        parser = command_instance.create_parser()
        namespace = parser.parse_args()
        command_instance.execute(namespace)
        return command_instance


def execute_command_inline(argv=None):
    """
    Execute a command using `python manage.py`
    """
    utility = Utility()
    try:
        utility.call_command(argv)
    except KeyboardInterrupt:
        from kryptone import logger
        logger.info('Program was stopped manually')
