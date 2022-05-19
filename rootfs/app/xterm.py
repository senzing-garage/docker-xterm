#!/usr/bin/python3

'''
# -----------------------------------------------------------------------------
# xterm.py Example python skeleton.
# -----------------------------------------------------------------------------
'''

# Import from standard library. https://docs.python.org/3/library/

# -*- coding: utf-8 -*-
import re
import sys

from app import main

if __name__ == '__main__':
    sys.argv[0] = re.sub(r'(-script\.pyw?|\.exe)?$', '', sys.argv[0])
    sys.exit(main())
