#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description:
version: 0.0.1
created: 2018-02-21
author: Ed Nykaza
dependencies:
    * requires Tidepool user's data in table (csv) format
license: BSD-2-Clause
TODO:
* []
"""


# %% load in required libraries
import pandas as pd
import datetime as dt
import os
#import json
#from pandas.io.json import json_normalize
import sys
import numpy as np
import argparse


# %% user inputs (choices to be made in order to run the code)
codeDescription = "Flatten json files to a table and save csv files"

parser = argparse.ArgumentParser(description=codeDescription)

parser.add_argument("-d",
                    "--date-stamp",
                    dest="dateStamp",
                    default=dt.datetime.now().strftime("%Y-%m-%d"),
                    help="date in '%Y-%m-%d' format of unique donor list" +
                    "(e.g., PHI-2018-03-02-uniqueDonorList)")

parser.add_argument("-o",
                    "--output-data-path",
                    dest="dataPath",
                    default="./data",
                    help="the output path where the data is stored")

#parser.add_argument("-s",
#                    "--start-index",
#                    dest="startIndex",
#                    default=0,
#                    help="donor index (integer) to start at")
#
#parser.add_argument("-e",
#                    "--end-index",
#                    dest="endIndex",
#                    default=-1,
#                    help="donor index (integer) to end at")

args = parser.parse_args()


# %% temp while building
args.dateStamp = "2018-02-28"


# %% define global variables
phiDateStamp = "PHI-" + args.dateStamp

# input folder(s)
donorFolder = os.path.join(args.dataPath, phiDateStamp + "-donor-data/")
if not os.path.isdir(donorFolder):
    sys.exit("{0} is not a directory".format(donorFolder))

donorCsvFolder = os.path.join(donorFolder, phiDateStamp + "-donorCsvFolder/")
if not os.path.isdir(donorCsvFolder):
    sys.exit("{0} is not a directory".format(donorCsvFolder))

# create output folder(s)
donorMetaDataFolder = os.path.join(donorFolder,
                                   phiDateStamp + "-donorMetaDataFolder/")
if not os.path.exists(donorMetaDataFolder):
    os.makedirs(donorMetaDataFolder)

# load in list of unique donors
uniqueDonors = pd.read_csv(donorFolder + phiDateStamp + "-uniqueDonorList.csv",
                           index_col="dIndex")

allMetaData = pd.DataFrame()


# %% functions
def statsByDataType(df, dataType, savePathName):
    allMetaStats = pd.DataFrame()
    groupedData = df.groupby(by=dataType)
    for dType in np.sort(df[df[dataType].notnull()][dataType].unique()):
        tempGroup = groupedData.get_group(dType).dropna(axis=1, how="all")
        metaByType = tempGroup.describe(include='all')
        if dType == "dual/square":
            dType = "dualSquare"  # TODO: this might change to "combination"
        byTypeStats = metaByType.add_prefix(dType + ".")
        byTypeStats.index.name = "stats"
        if dataType == "subType":
            typeVar = tempGroup.type.describe()["top"]
            byTypeStats.to_csv(savePathName.format(typeVar, dType))
        else:
            byTypeStats.to_csv(savePathName.format(dType))
        allMetaStats = pd.concat([allMetaStats, byTypeStats], axis=1)
    return allMetaStats


# %% start of code
for dIndex in uniqueDonors.index:
    userID = uniqueDonors.loc[dIndex, "userID"]
    csvFileName = os.path.join(donorCsvFolder, "PHI-" + userID + ".csv")
    if os.path.exists(csvFileName):
        phiUserID = "PHI-" + userID
        userMetaDataFolder = os.path.join(donorMetaDataFolder, phiUserID)
        if not os.path.exists(userMetaDataFolder):
            os.makedirs(userMetaDataFolder)

        data = pd.read_csv(os.path.join(donorCsvFolder, phiUserID + ".csv"),
                           low_memory=False)

        metaAll = data.describe(include='all')
        allStats = metaAll.add_prefix("all.")
        allStats.index.name = "stats"
        allStats.to_csv(os.path.join(userMetaDataFolder,
                                     phiUserID + "-allData-metadata.csv"))

        # get stats by type
        outputPathName = os.path.join(userMetaDataFolder,
                                      phiUserID + "-{0}-metadata.csv")

        allByTypeStats = statsByDataType(data, "type", outputPathName)
        allStats = pd.concat([allStats, allByTypeStats], axis=1)

        # get stats by subType
        if "subType" in list(data):
            outputPathName = os.path.join(userMetaDataFolder,
                                          phiUserID + "-{0}-{1}-metadata.csv")
            allBySubTypeStats = statsByDataType(data,
                                                "subType",
                                                outputPathName)
            allStats = pd.concat([allStats, allBySubTypeStats], axis=1)

        # combine all stats
        allStats.to_csv(os.path.join(userMetaDataFolder,
                                     phiUserID +
                                     "-allTypesCombined-metadata.csv"))

        # flatten all stats into one row
        allStatsFlattened = pd.DataFrame(allStats.unstack(),
                                         columns=[dIndex]).T
        allStatsFlattened = allStatsFlattened.dropna(axis=1, how="all")
        allStatsFlattened.columns = \
            ['.'.join(col).strip() for col in allStatsFlattened.columns.values]

        # merge data into one dataFrame
        allMetaData = pd.concat([allMetaData, allStatsFlattened], axis=0)

        # output progress
        print(round((dIndex + 1) / (len(uniqueDonors)) * 100, 1),
              "% ", dIndex, "of", len(uniqueDonors))

allMetaData.index.name = "dIndex"
uniqueDonors = pd.concat([uniqueDonors, allMetaData], axis=1)
uniqueDonors.to_csv(os.path.join(donorFolder,
                                 phiDateStamp +
                                 "-donorMetaDataFolder-metadata.csv"))
