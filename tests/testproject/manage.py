#!/usr/bin/env python

import os
import sys

from kryptone.management import execute_command_inline

if __name__ == '__main__':
    os.environ.setdefault('KRYPTONE_SPIDER', 'tests.testproject')
    execute_command_inline(sys.argv)
