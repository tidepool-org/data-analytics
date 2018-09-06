#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: load csv data
created: 2018-02-21
author: Ed Nykaza
license: BSD-2-Clause
"""

import pandas as pd


def load_csv(dataPathAndName):
    df = pd.read_csv(dataPathAndName, low_memory=False)
    return df
