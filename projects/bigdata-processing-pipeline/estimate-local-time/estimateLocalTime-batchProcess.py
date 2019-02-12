#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: Estimate local time
version: 0.0.1
created: 2018-10-23
author: Ed Nykaza
dependencies:
    * estimate-local-time.py
license: BSD-2-Clause
"""


# %% REQUIRED LIBRARIES
import os
import sys
import datetime as dt
import argparse
import subprocess as sub
import time
from multiprocessing import Pool

# load tidals package locally if it does not exist globally
import importlib

if importlib.util.find_spec("tidals") is None:
    tidalsPath = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "tidepool-analysis-tools")
    )
    if tidalsPath not in sys.path:
        sys.path.insert(0, tidalsPath)
import tidals as td

startTime = time.time()
print("starting at " + dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


# %% USER INPUTS
codeDescription = (
    "A batch processing or wrapper script to run the estimate-local-time.py"
)
parser = argparse.ArgumentParser(description=codeDescription)

parser.add_argument(
    "-d",
    "--date-stamp",
    dest="dateStamp",
    default=dt.datetime.now().strftime("%Y-%m-%d"),
    help="date in '%Y-%m-%d' format needed to call unique "
    + "donor list (e.g., PHI-2018-03-02-uniqueDonorList)",
)

parser.add_argument(
    "--start-date",
    dest="startDate",
    default="2010-01-01",
    help="filter data by startDate and endDate",
)

parser.add_argument(
    "-ow",
    "--overWrite",
    dest="overWrite",
    default=False,
    help="Specify if you want to overwrite a file that has already"
    + "been processed, False if NO, True if YES",
)

args = parser.parse_args()


# %% SET UP PATHS
dataPath = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "data", "PHI-" + args.dateStamp + "-donor-data"
    )
)

donorInfoPath = os.path.join(dataPath, "PHI-" + args.dateStamp + "-uniqueDonorList.csv")
donors = td.load.load_csv(donorInfoPath)

jsonDataPath = os.path.join(dataPath, "PHI-" + args.dateStamp + "-donorJsonData")
localTimeEstimateDataPath = os.path.join(
    dataPath, "PHI-" + args.dateStamp + "-localTime"
)

# create localTimeEstimateDataPath folders
if not os.path.exists(localTimeEstimateDataPath):
    os.makedirs(localTimeEstimateDataPath)

localTimeEstimateDaySeriesPath = os.path.join(
    dataPath, args.dateStamp + "-localTime-daySeries"
)

# create localTimeEstimateDataPath folders
if not os.path.exists(localTimeEstimateDaySeriesPath):
    os.makedirs(localTimeEstimateDaySeriesPath)


# %% FUNCTIONS
def run_estimate_local_time(dIndex):
    userID = donors.userID[dIndex]
    fileName = "PHI-" + str(userID)
    jsonFileName = os.path.join(jsonDataPath, fileName + ".json")
    fileSize = os.stat(jsonFileName).st_size
    if fileSize > 1000:
        localTimeEstimateDataPathAndName = os.path.join(
            localTimeEstimateDataPath, fileName + ".csv"
        )
        # if estimate has not yet been made OR if the estimate has been made, but overWrite = True
        if (not os.path.exists(localTimeEstimateDataPathAndName)) | (
            (os.path.exists(localTimeEstimateDataPathAndName)) & (args.overWrite)
        ):

            print(
                "starting with index=" + str(dIndex),
                "file size is: " + str(round(fileSize / 1e6, 1)) + "MB",
            )
            # local time estimate
            p = sub.Popen(
                [
                    "python",
                    "estimate-local-time.py",
                    "-i",
                    jsonFileName,
                    "-o",
                    localTimeEstimateDataPath,
                    "--day-series-output-path",
                    localTimeEstimateDaySeriesPath,
                    "--start-date",
                    args.startDate,
                ],
                stdout=sub.PIPE,
                stderr=sub.PIPE,
            )

            output, errors = p.communicate()
            output = output.decode("utf-8")
            errors = errors.decode("utf-8")

            print(
                "finished with index=" + str(dIndex),
                " output: " + output,
                "errors: " + errors,
            )
        else:
            print("skipped index=" + str(dIndex) + " because is was already processed")
    else:
        print(
            "skipped index="
            + str(dIndex)
            + " because file size is: "
            + str(fileSize)
            + "Bytes"
        )

    return


# %% main code execution

# use multiple cores to process
pool = Pool(os.cpu_count())
pool.map(run_estimate_local_time, donors.dIndex)
pool.close()

endTime = time.time()
print("finshed at " + dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
print("total duration was " + str(round((endTime - startTime) / 60, 1)) + " minutes")
