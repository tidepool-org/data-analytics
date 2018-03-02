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


# %% define global variables
phiDateStamp = "PHI-" + args.dateStamp

donorFolder = os.path.join(args.dataPath, phiDateStamp + "-donor-data/")
if not os.path.isdir(donorFolder):
    sys.exit("{0} is not a directory".format(donorFolder))

donorJsonDataFolder = donorFolder + phiDateStamp + "-donorJsonData/"
if not os.path.isdir(donorJsonDataFolder):
    sys.exit("{0} is not a directory".format(donorJsonDataFolder))

# create output folders
donorFlatJsonDataFolder = donorFolder + phiDateStamp + "-donorFlatJsonData/"
if not os.path.exists(donorFlatJsonDataFolder):
    os.makedirs(donorFlatJsonDataFolder)

donorCsvDataFolder = donorFolder + phiDateStamp + "-donorCsvDataByType/"
if not os.path.exists(donorCsvDataFolder):
    os.makedirs(donorCsvDataFolder)

# load in list of unique donors
uniqueDonors = pd.read_csv(donorFolder + phiDateStamp + "-uniqueDonorList.csv",
                           index_col="dIndex")

allDiagnostics = pd.DataFrame()

startIndex = int(args.startIndex)
endIndex = int(args.endIndex)
if endIndex == -1:
    if startIndex == 0:
        endIndex = len(uniqueDonors)
    else:
        endIndex = startIndex + 1

metadataFilePathName = donorFolder + phiDateStamp + \
    "-donorMetadata-" + str(startIndex) + "-" + str(endIndex) + ".csv"


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


# %% start of code
for dIndex in range(startIndex, endIndex):
    diagnostics = pd.DataFrame(index=[dIndex])
    userID = uniqueDonors.userID[dIndex]
    diagnostics["userID"] = userID
    inputFilePathName = os.path.join(donorJsonDataFolder,
                                     "PHI-" + userID + ".json")
    fileSize = os.stat(inputFilePathName).st_size
    diagnostics["fileSizeKB"] = int(fileSize / 1000)
    flatJsonFilePathName = donorFlatJsonDataFolder + "PHI-" + userID + ".csv"
    # if the json file already exists, do NOT pull it again
    if not os.path.exists(flatJsonFilePathName):
        if fileSize > 1000:
            if fileSize > 250E6:  # flag condition where download is > 250MB
                diagnostics["errorMessage"] = \
                    "download manually until commandline tools are fixed"
            with open(inputFilePathName, 'r') as f:
                datastore = json.load(f)

                # “Normalize” semi-structured JSON data into a flat table
                data = json_normalize(datastore)

                # flatten embedded json, if it exists
                data = flattenJson(data)

                # remove [] from annotations field
                data = removeBrackets(data, "annotations")

                # flatten again, if ebedded json within the embedded json
                data = flattenJson(data)

                diagnostics["nRows"] = len(data)
                diagnostics["nColumns"] = len(list(data))

                # save the flattened json file
                data.index.name = "jsonRowIndex"
                data.to_csv(flatJsonFilePathName)

                # break data by type and save
                csvFilePath = donorCsvDataFolder + "PHI-" + userID + "/"
                if not os.path.exists(csvFilePath):
                    os.makedirs(csvFilePath)
                csvUserFileName = csvFilePath + "PHI-" + userID
                saveByType(data, csvUserFileName)

        else:
            diagnostics["errorMessage"] = "no data"
    else:
        print(dIndex, "already processed")

    print(dIndex, "of", endIndex)

    allDiagnostics = pd.concat([allDiagnostics, diagnostics])

# %% save output
uniqueDonors = pd.merge(uniqueDonors,
                        allDiagnostics,
                        how="left",
                        on="userID")

uniqueDonors.index.name = "dIndex"
uniqueDonors.to_csv(metadataFilePathName)
