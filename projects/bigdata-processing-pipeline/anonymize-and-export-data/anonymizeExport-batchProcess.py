#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: Estimate local time
version: 0.0.1
created: 2018-10-23
author: Ed Nykaza
dependencies:
    * anonymize-and-export.py
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
    tidalsPath = os.path.abspath(os.path.join(os.path.dirname(__file__),
                      "..", "..", "tidepool-analysis-tools"))
    if tidalsPath not in sys.path:
        sys.path.insert(0, tidalsPath)
import tidals as td

envPath = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if envPath not in sys.path:
    sys.path.insert(0, envPath)
import environmentalVariables


startTime = time.time()
print("starting at " + dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


# %% USER INPUTS
codeDescription = "A batch processing or wrapper script to run the anonymize-and-export.py"
parser = argparse.ArgumentParser(description=codeDescription)

parser.add_argument("-d",
                    "--date-stamp",
                    dest="dateStamp",
                    default=dt.datetime.now().strftime("%Y-%m-%d"),
                    help="date in '%Y-%m-%d' format needed to call unique " +
                    "donor list (e.g., PHI-2018-03-02-uniqueDonorList)")

parser.add_argument("--start-date",
                    dest="startDate",
                    default="2010-01-01",
                    help="filter data by startDate and endDate")

parser.add_argument("--data-field-list",
                    dest="dataFieldExportList",
                    default=os.path.abspath(
                            os.path.join(
                            os.path.dirname(__file__),
                            "..", "data",
                            "dataFieldExportList.csv")),
                    help="a csv file that contains a list of fields to export")

parser.add_argument("-ow",
                    "--overWrite",
                    dest="overWrite",
                    default=False,
                    help="Specify if you want to overwrite a file that has already" + \
                    "been processed, False if NO, True if YES")

args = parser.parse_args()


# %% SET UP PATHS
dataPath = os.path.abspath(
            os.path.join(os.path.dirname(__file__),
                         "..", "data",
                         "PHI-" + args.dateStamp + "-donor-data"))

donorInfoPath = os.path.join(dataPath, "PHI-" + args.dateStamp + "-uniqueDonorList.csv")
donors = td.load.load_csv(donorInfoPath)

csvDataPath = os.path.join(dataPath, "PHI-" + args.dateStamp + "-localTime")
anonExportDataPath = os.path.join(dataPath, args.dateStamp + "-anonimized")

# create anonExportDataPath folders
if not os.path.exists(anonExportDataPath):
    os.makedirs(anonExportDataPath)


# %% FUNCTIONS
def run_estimate_local_time(dIndex):
    userID = donors.userID[dIndex]
    hashID = donors.hashID[dIndex]
    fileName = "PHI-" + str(userID)
    csvFileName = os.path.join(csvDataPath, fileName + ".csv")
    fileSize = os.stat(csvFileName).st_size
    if fileSize > 1000:
        anonExportDataPathAndName = \
            os.path.join(anonExportDataPath, "hashID" + ".csv")
        # if anonExport has not yet been made OR if tyou want to overwrite (overWrite = True)
        if ((not os.path.exists(anonExportDataPathAndName)) |
                ((os.path.exists(anonExportDataPathAndName)) & (args.overWrite))):

            print("starting with index=" + str(dIndex),
                  "file size is: " + str(round(fileSize/1E6, 1)) + "MB")
            # anonymize and export
            p = sub.Popen(["python", "anonymize-and-export.py",
                           "-i", csvFileName,
                           "-o", anonExportDataPath,
                           "--data-field-list", args.dataFieldExportList,
                           "--salt", os.environ["BIGDATA_SALT"],
                           "--output-format", "csv",
                           "--start-date", args.startDate], stdout=sub.PIPE, stderr=sub.PIPE)

            output, errors = p.communicate()
            output = output.decode("utf-8")
            errors = errors.decode("utf-8")

            print("finished with index=" + str(dIndex),
                 " output: " + output, "errors: " + errors)
        else:
            print("skipped index=" + str(dIndex) + " because is was already processed")
    else:
        print("skipped index=" + str(dIndex) + " because file size is: " + str(fileSize) + "Bytes")

    return


# %% main code execution

# use multiple cores to process
pool = Pool(os.cpu_count())
pool.map(run_estimate_local_time, donors.dIndex)
pool.close()

endTime = time.time()
print("finshed at " + dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
print("total duration was " + str(round((endTime - startTime) / 60, 1)) + " minutes")
