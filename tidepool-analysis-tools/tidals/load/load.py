#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: data loading tools for tidals (tidepool data analytics tools)
created: 2018-02-21
author: Ed Nykaza
license: BSD-2-Clause
"""

import pandas as pd
import os
import sys

def load_json(dataPathAndName):
    df = pd.read_json(dataPathAndName, orient="records")
    return df


def load_csv(dataPathAndName):
    df = pd.read_csv(dataPathAndName, low_memory=False)
    return df


def load_xlsx(dataPathAndName):
    # load xlsx
    df = pd.read_excel(dataPathAndName, sheet_name=None, ignore_index=True)
    cdf = pd.concat(df.values(), ignore_index=True)
    cdf = cdf.set_index('jsonRowIndex')
    return cdf


def load_data(inputFile):
    if os.path.isfile(inputFile):
        if os.stat(inputFile).st_size > 2:
            if inputFile[-4:] == "json":
                inputData = load_json(inputFile)
                fileName = os.path.split(inputFile)[-1][:-5]
            elif inputFile[-4:] == "xlsx":
                inputData = load_xlsx(inputFile)
                fileName = os.path.split(inputFile)[-1][:-5]
            elif inputFile[-3:] == "csv":
                inputData = load_csv(inputFile)
                fileName = os.path.split(inputFile)[-1][:-4]
            else:
                sys.exit("{0} is not a json, xlsx, or csv".format(inputFile))
        else:
            sys.exit("{0} contains too little data".format(inputFile))
    else:
        sys.exit("{0} does not exist".format(inputFile))

    # if fileName has PHI in it, remove PHI to get userID
    if "PHI" in fileName.upper():
        fileName = fileName[4:]

    return inputData, fileName
