#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: gather the ouput from get users settings and events
version: 0.0.1
created: 2019-01-30
author: Ed Nykaza
dependencies:
    *
license: BSD-2-Clause
"""

# %% REQUIRED LIBRARIES
import pandas as pd
import datetime as dt
import os
import argparse
import glob


# %% USER INPUTS (ADD THIS IN LATER)
codeDescription = "Get user's settings and events"
parser = argparse.ArgumentParser(description=codeDescription)

parser.add_argument("-d",
                    "--dataPulledDate",
                    dest="dataPulledDate",
                    default="2018-09-28",
                    help="date in '%Y-%m-%d' format of unique donor list" +
                    "(e.g., PHI-2018-03-02-uniqueDonorList)")

parser.add_argument("-p",
                    "--dataProcessedDate",
                    dest="dataProcessedDate",
                    default="2019-01-21",
                    help="date in '%Y-%m-%d' format")

args = parser.parse_args()


# %% START OF CODE
dataPulledDate = args.dataPulledDate
dataProcessedDate = pd.to_datetime(args.dataProcessedDate)

phiDate = "PHI-" + dataPulledDate
donorPath = os.path.join(
        "..", "bigdata-processing-pipeline",
        "data", phiDate + "-donor-data")

outputPath = os.path.join(donorPath, "settings-and-events")

for name in ["allMetadata", "allAgeANDylwSummaries",
             "allAgeSummaries", "allYlwSummaries",
             "basalEvents", "bolusEvents"]:
    allDF = pd.DataFrame()
    if name.startswith("all"):
        files = glob.glob(os.path.join(outputPath, name + '*'))
    else:
        files = glob.glob(
                os.path.join(outputPath, "data", "**", "*-" + name + ".csv"))
    for f in files:
        dateModified = \
            pd.to_datetime(dt.datetime.fromtimestamp(os.path.getmtime(f)))
        if dateModified > dataProcessedDate:
            tempDF = pd.read_csv(f, low_memory=False)
            tempDF.rename(
                    columns={'Unnamed: 0': 'originalIndex'}, inplace=True)
            tempDF["from"] = f
            allDF = pd.concat([allDF, tempDF], ignore_index=True, sort=False)
    allDF.to_csv(os.path.join(outputPath, "combined-" + name + ".csv"))
    print("completed " + name)
