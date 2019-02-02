#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: Example code using the loop_report class.
Created on Fri Jan 25 06:55:48 2019

@author: ed
"""

from loop_report import LoopReport
import pandas as pd
import json
import os

# %% file name and path
file_path = os.path.join("..", "tests", "parsers", "files")
file_name = "LoopReport"

# %% parse file
lr = LoopReport()
loop_dict = lr.parse_by_file(path=file_path, file_name="%s.md" % file_name)

# %% save parsed file
with open(file_path + file_name + "-data.json", "w") as fp:
    json.dump(loop_dict, fp, sort_keys=True, indent=4)

# %% put data into a dataframe and save
loop_df = pd.DataFrame(columns=loop_dict.keys(), index=[0])
loop_df = loop_df.astype("object")
for k in loop_dict.keys():
    loop_df[k][0] = loop_dict[k]

loop_df.to_csv(file_path + file_name + "-data-in-columns.csv", index_label="index")
loop_df.T.to_csv(file_path + file_name + "-data-in-rows.csv", index_label="index")
