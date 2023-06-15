import sys

from kryptone import management

if __name__ == '__main__':
    management.execute_command_inline(argv=sys.argv)
