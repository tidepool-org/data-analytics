#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 25 06:55:48 2019

@author: ed
"""

from loop_report import LoopReport
import json

# %% file name and path
file_path = "/Users/ed/Desktop/"
file_name = "2019-01-16 08-39-03-06-00"

# %% parse file
lr = LoopReport()
loop_dict = lr.parse_by_file(
        path=file_path,
        file_name="Loop Report %s.md" % file_name
)

# %% save parsed file
with open(file_name + '-data.json', 'w') as fp:
    json.dump(loop_dict, fp, sort_keys=True, indent=4)
