#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: example script of how to load the tidals package
created: 2018-02-21
author: Ed Nykaza
license: BSD-2-Clause
"""


# PLEASE NOTE: THESE 10 LINES ARE NEEDED TO LOAD THE tidals PACKAGE
# ALSO NOTE: THIS PACKAGE IS STILL IN DEVELOPMENT
import sys
import os
cwd = os.getcwd()
# NOTE: if you renamed the root directory of the data-analytics repository,
# enter that name here:
nameDataAnalyticsRepository = "data-analytics"
packagePath = cwd[:(cwd.find(nameDataAnalyticsRepository) +
                    len(nameDataAnalyticsRepository) + 1)]
sys.path.append(packagePath)
sys.path.append(os.path.join(packagePath, "tidals"))
import tidals as td
import pandas as pd


# %% load in example data with the tidals package
dataPath = os.path.join(packagePath, "example-data", "example-from-j-jellyfish.csv")
data = td.load_csv(dataPath)

# get just the cgm data (utc-time and mmol/L values)
cgm = data.loc[data.type == "cbg", ["time", "value"]]

# round data to the nearest 15 minutes
cgm = td.round_time(cgm, timeIntervalMinutes=15)
