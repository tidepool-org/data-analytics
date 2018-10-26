#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: get-list-of-all-column-headings
version: 0.0.1
created: 2018-10-23
author: Ed Nykaza
dependencies:
    * donor json data
license: BSD-2-Clause
"""


# %% REQUIRED LIBRARIES
import os
import sys
import pandas as pd
import datetime as dt
import argparse
import time
# load tidals package locally if it does not exist globally
import importlib
if importlib.util.find_spec("tidals") is None:
    tidalsPath = os.path.abspath(os.path.join(os.path.dirname(__file__),
                      "..", "..", "tidepool-analysis-tools"))
    if tidalsPath not in sys.path:
        sys.path.insert(0, tidalsPath)
import tidals as td


# %% CODE METADATA
startTime = time.time()
print("starting at " + dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


# %% USER INPUTS
codeDescription = "A batch processing or wrapper script to get a list of all column headings"
parser = argparse.ArgumentParser(description=codeDescription)

parser.add_argument("-d",
                    "--date-stamp",
                    dest="dateStamp",
                    default=dt.datetime.now().strftime("%Y-%m-%d"),
                    help="date in '%Y-%m-%d' format needed to call unique " +
                    "donor list (e.g., PHI-2018-03-02-uniqueDonorList)")

args = parser.parse_args()


# %% SET UP PATHS
dataPath = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                        "..", "data", "PHI-" + args.dateStamp + "-donor-data"))

donorInfoPath = os.path.join(dataPath, "PHI-" + args.dateStamp + "-uniqueDonorList.csv")
donors = td.load.load_csv(donorInfoPath)
jsonDataPath = os.path.join(dataPath, "PHI-" + args.dateStamp + "-donorJsonData")


# %% FUNCTIONS
uniqueColHeadings = set()
i = 0
for dIndex in donors.index:
    userID = donors.userID[dIndex]
    fileName = "PHI-" + str(userID)
    jsonFileName = os.path.join(jsonDataPath, fileName + ".json")
    fileSize = os.stat(jsonFileName).st_size
    if fileSize > 1000:
        i = i + 1
        data = td.load.load_json(jsonFileName)
        uniqueColHeadings = uniqueColHeadings.union(set(list(data)))
        print(i, len(list(uniqueColHeadings)))

allCols = pd.DataFrame(list(uniqueColHeadings), columns=["colHeading"])
allCols = allCols.sort_values(by="colHeading").reset_index(drop=True)
allCols.to_csv("all-col-headings-" + args.dateStamp + ".csv")


# %% CODE METADATA
endTime = time.time()
print("finshed at " + dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
print("total duration was " + str(round((endTime - startTime) / 60, 1)) + " minutes")
