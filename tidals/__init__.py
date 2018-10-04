#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: initialize the tidepool data analytics tools (tidals) python pacakge
version: 0.0.1
created: 2018-07-21
author: Ed Nykaza
license: BSD-2-Clause
"""

# add the tidals path to sys path if it doesn't already exist
import os, sys
dirname = os.path.dirname(os.path.realpath(__file__))
if dirname not in sys.path:
    sys.path.insert(0, dirname)

# List of functions in the tidals package
from load import load_json, load_csv, load_xlsx, load_data
from clean import remove_duplicates, round_time, remove_brackets, flatten_json

# remove these modules and variables left over from the sys path
# TODO: there has to be a better way to load in the path
del os, sys, dirname
