#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: example script of how to load the tidals package
created: 2018-02-21
author: Ed Nykaza
license: BSD-2-Clause
"""

import os
import sys

nameDataAnalyticsRepository = "data-analytics"
packagePath = os.getcwd()[:(os.getcwd().find(nameDataAnalyticsRepository) +
                          len(nameDataAnalyticsRepository) + 1)]
sys.path.append(os.path.abspath(os.path.join(packagePath, "tidepool-analysis-tools")))
import tidals as td


# %% load in example data with the tidals package
dataPath = os.path.join(packagePath, "examples", "example-data", "example-from-j-jellyfish.csv")
data = td.load_csv(dataPath)

# get just the cgm data (utc-time and mmol/L values)
cgm = data.loc[data.type == "cbg", ["time", "value"]]

# round data to the nearest 15 minutes
cgm = td.round_time(cgm, timeIntervalMinutes=15)
