#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: initialize the tidepool data analytics tools (tidals) python pacakge
version: 0.0.1
created: 2018-07-21
author: Ed Nykaza
license: BSD-2-Clause
"""

# List of functions in the tidals package
from load import load_json, load_csv, load_xlsx, load_data
from clean import remove_duplicates, round_time, remove_brackets, flatten_json 
