#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: flatten json files to a table and save csv files
version: 0.0.1
created: 2018-02-21
author: Ed Nykaza
dependencies:
    * requires Tidepool user's data in json format
license: BSD-2-Clause
TODO:
* [] rewrite code to take advantage of parrallel processing, given that
code takes so long to run
* [] command line tools need to be updated to be able to download json files
that are greater than 250 MB
"""

# %% load in required libraries
import pandas as pd
import datetime as dt
import os
import json
from pandas.io.json import json_normalize
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

parser.add_argument("-s",
                    "--start-index",
                    dest="startIndex",
                    default=0,
                    help="donor index (integer) to start at")

parser.add_argument("-e",
                    "--end-index",
                    dest="endIndex",
                    default=-1,
                    help="donor index (integer) to end at")

args = parser.parse_args()


# %% define functions
def flattenJson(df):
    # get a list of columnHeadings
    columnHeadings = list(df)

    # loop through each columnHeading
    for colHead in columnHeadings:
        # if the df field has embedded json
        if "{" in df[df[colHead].notnull()][colHead].astype(str).str[0].values:
            # grab the data that is in brackets
            jsonBlob = df[colHead][df[colHead].astype(str).str[0] == "{"]
            # replace those values with nan
            df.loc[jsonBlob.index, colHead] = np.nan
            # turn jsonBlog to dataframe
            newDataFrame = jsonBlob.apply(pd.Series)
            newDataFrame = newDataFrame.add_prefix(colHead + '.')
            newColHeadings = list(newDataFrame)

            # put df back into the main dataframe
            for newColHeading in newColHeadings:
                tempDataFrame = newDataFrame[newColHeading]
                df = pd.concat([df, tempDataFrame], axis=1)

    return df


def removeBrackets(df, fieldName):
    if fieldName in list(df):
        df.loc[df[fieldName].notnull(), fieldName] = \
            df.loc[df[fieldName].notnull(), fieldName].str[0]

    return df


def saveByType(df, outputFileName):
    uniqueTypeNames = list(df.type.unique())
    if np.nan in uniqueTypeNames:
        uniqueTypeNames.remove(np.nan)
    groupedData = df.groupby(by="type")

    # save each type of df
    for typeName in uniqueTypeNames:
        tempGroup = groupedData.get_group(typeName).dropna(axis=1, how="all")
        tempGroup.to_csv(outputFileName + "-" + typeName + ".csv")

    return


def defineStartAndEndIndex(args):
    startIndex = int(args.startIndex)
    endIndex = int(args.endIndex)
    if endIndex == -1:
        if startIndex == 0:
            endIndex = len(uniqueDonors)
        else:
            endIndex = startIndex + 1

    return startIndex, endIndex


def tempRemoveFields(df):
    removeFields = ["basalSchedules",
                    "bgTarget",
                    "carbRatio",
                    "insulinSensitivity",
                    "payload",
                    "suppressed"]

    tempRemoveFields = list(set(data) & set(removeFields))
    tempDf = data[tempRemoveFields]
    df = df.drop(columns=tempRemoveFields)

    return df, tempDf


# %% define global variables
phiDateStamp = "PHI-" + args.dateStamp

donorFolder = os.path.join(args.dataPath, phiDateStamp + "-donor-data/")
if not os.path.isdir(donorFolder):
    sys.exit("{0} is not a directory".format(donorFolder))

donorJsonDataFolder = donorFolder + phiDateStamp + "-donorJsonData/"
if not os.path.isdir(donorJsonDataFolder):
    sys.exit("{0} is not a directory".format(donorJsonDataFolder))

# create output folders
donorCsvFolder = os.path.join(donorFolder, phiDateStamp + "-donorCsvFolder/")
if not os.path.exists(donorCsvFolder):
    os.makedirs(donorCsvFolder)

donorMetaDataFolder = os.path.join(donorFolder,
                                   phiDateStamp + "-donorMetaDataFolder/")
if not os.path.exists(donorMetaDataFolder):
    os.makedirs(donorMetaDataFolder)

# load in list of unique donors
uniqueDonors = pd.read_csv(donorFolder + phiDateStamp + "-uniqueDonorList.csv",
                           index_col="dIndex")

allDiagnostics = pd.DataFrame()

# define start and end index
startIndex, endIndex = defineStartAndEndIndex(args)

#startIndex = int(args.startIndex)
#endIndex = int(args.endIndex)
#if endIndex == -1:
#    if startIndex == 0:
#        endIndex = len(uniqueDonors)
#    else:
#        endIndex = startIndex + 1

metadataFilePathName = donorFolder + phiDateStamp + \
    "-donorMetadata-" + str(startIndex) + "-" + str(endIndex) + ".csv"


# %% start of code
for dIndex in range(startIndex, endIndex):
    metadata = pd.DataFrame(index=[dIndex])
    userID = uniqueDonors.userID[dIndex]
    metadata["userID"] = userID
    inputFilePathName = os.path.join(donorJsonDataFolder,
                                     "PHI-" + userID + ".json")
    fileSize = os.stat(inputFilePathName).st_size
    metadata["fileSizeKB"] = int(fileSize / 1000)
    csvFilePathName = donorCsvFolder + "PHI-" + userID + ".csv"
    # if the csv file already exists, do NOT pull it again
    if not os.path.exists(csvFilePathName):
        if fileSize > 1000:
            if fileSize > 250E6:  # flag condition where download is > 250MB
                metadata["errorMessage"] = \
                    "download manually until commandline tools are fixed"

            with open(inputFilePathName, 'r') as f:
                datastore = json.load(f)

                # “Normalize” semi-structured JSON data into a flat table
                data = json_normalize(datastore)

                # remove fields that we don't want to flatten
                data, holdData = tempRemoveFields(data)

#                removeFields = ["basalSchedules",
#                                    "carbRatios",
#                                    "insulinSensitivities",
#                                    "payload",
#                                    "suppressed"]
#                tempRemoveFields = list(set(data) & set(removeFields))
#                holdData = data[tempRemoveFields]
#                data = data.drop(columns=tempRemoveFields)

                # remove [] from annotations field
                data = removeBrackets(data, "annotations")

                # flatten embedded json, if it exists
                data = flattenJson(data)

                # add the fields that were removed back in
                data = pd.concat([data, holdData], axis=1)


#                # flatten again, if ebedded json within the embedded json
#                data = flattenJson(data)

#                metadata["nRows"] = len(data)
#                metadata["nColumns"] = len(list(data))

                # save the flattened json file
                data.index.name = "jsonRowIndex"
                data.to_csv(csvFilePathName)

#                # break data by type and save
#                csvFilePath = donorMetaDataFolder + "PHI-" + userID + "/"
#                if not os.path.exists(csvFilePath):
#                    os.makedirs(csvFilePath)
#                csvUserFileName = csvFilePath + "PHI-" + userID
#                saveByType(data, csvUserFileName)

        else:
            metadata["errorMessage"] = "no data"
    else:
        print(dIndex, "already processed")

    print(round(dIndex/(endIndex - startIndex) * 100,1),
          "% ", dIndex, "of", endIndex)

    allDiagnostics = pd.concat([allDiagnostics, metadata])

# %% save output
#uniqueDonors = pd.merge(uniqueDonors,
#                        allDiagnostics,
#                        how="left",
#                        on="userID")

allDiagnostics.index.name = "dIndex"
allDiagnostics.to_csv(metadataFilePathName)
