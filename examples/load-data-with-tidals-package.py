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
import importlib
# load tidals package locally if it does not exist globally
if importlib.util.find_spec("tidals") is None:
    tidalsPath = os.path.abspath(
                    os.path.join(
                    os.path.dirname(__file__),
                    "..", "tidepool-analysis-tools"))
    if tidalsPath not in sys.path:
        sys.path.insert(0, tidalsPath)
import tidals as td


# %% load in example data with the tidals package
dataPath = os.path.join(os.path.dirname(__file__), "example-data", "example-from-j-jellyfish.csv")
data, fileName = td.load.load_data(dataPath)

# get just the cgm data (utc-time and mmol/L values)
cgm = data.loc[data.type == "cbg", ["time", "value"]]

# round data to the nearest 15 minutes
cgm = td.clean.round_time(cgm, timeIntervalMinutes=15)
