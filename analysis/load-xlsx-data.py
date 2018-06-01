#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: Load donor data in xlsx format into pandas
version: 0.0.1
created: 2018-05-10
author: Ed Nykaza
dependencies:
    * requires tidepool analysis environment (see readme for instructions), OR
it requires that the xlrd module is installed in your environment

license: BSD-2-Clause
"""

import pandas as pd
import os

# load an example xlsx file
xlsxPathAndFileName = os.path.join("..", "example-data", "PHI-example.xlsx")

# load xlsx
df = pd.read_excel(xlsxPathAndFileName, sheet_name=None, ignore_index=True)

# create a data frame or table that combines data from all xlsx sheets
cdf = pd.concat(df.values(), ignore_index=True)
cdf = cdf.set_index('jsonRowIndex')

# save as csv a file
outpath = os.path.join("..", "example-data", "PHI-example")
cdf.to_csv(outpath + ".csv")
