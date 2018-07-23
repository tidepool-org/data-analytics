#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: example script of how to load the tpanalyze package
created: 2018-02-21
author: Ed Nykaza
license: BSD-2-Clause
"""


# PLEASE NOTE: THESE 6 LINES ARE NEEDED TO LOAD THE TPANALYZTICS PACKAGE
# THIS PACKAGE IS IN DEVELOPMENT
import sys
import os
cwd = os.getcwd()
packagePath = cwd[:(cwd.find("data-analytics") + 15)]
sys.path.append(packagePath)
sys.path.append(os.path.join(packagePath, "tpanalyze"))
import tpanalyze as tp


# %% load in example data with the tpanalyze package
dataPath = os.path.join("..", "example-data", "example-from-j-jellyfish.csv")
data = tp.load_csv(dataPath)
