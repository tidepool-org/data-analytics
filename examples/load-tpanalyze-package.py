#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: example script of how to load the tpanalyze package
created: 2018-02-21
author: Ed Nykaza
license: BSD-2-Clause
"""


# PLEASE NOTE: THESE 10 LINES ARE NEEDED TO LOAD THE TPANALYZE PACKAGE
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
sys.path.append(os.path.join(packagePath, "tpanalyze"))
import tpanalyze as tp
import pandas as pd


# %% load in example data with the tpanalyze package
dataPath = os.path.join("..", "example-data", "example-from-j-jellyfish.csv")
data = tp.load_csv(dataPath)

# get just the cgm data
cgm = data.type

# round data to the nearest 5 minutes
data = tp.round_time(data, 5)
