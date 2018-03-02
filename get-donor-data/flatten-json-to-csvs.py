#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description:
version: 0.0.1
created:
author: Ed Nykaza
dependencies:
    *
license: BSD-2-Clause
TODO:
* [] rewrite code to take advantage of parrallel processing, given that
code takes so long to run
* [] commandn line tools need to be updated to be able to download json files
that are greater than 250 MB
"""

# %% load in required libraries
import pandas as pd
import os
import json
from pandas.io.json import json_normalize
import sys
import numpy as np


# %% user inputs (choices to be made to run code)
securePath = "/tidepoolSecure/data/"
dateStamp = "2018-02-28"


# %% define global variables
phiDateStamp = "PHI-" + dateStamp

donorFolder = securePath + phiDateStamp + "-donor-data/"
if not os.path.exists(donorFolder):
    sys.exit("ERROR: This folder should exist")

donorJsonDataFolder = donorFolder + phiDateStamp + "-donorJsonData/"
if not os.path.exists(donorJsonDataFolder):
    sys.exit("ERROR: This folder should exist")

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

startIndex = 0
endIndex = len(uniqueDonors)

metadataFilePathName = donorFolder + phiDateStamp + \
    "-donorMetadata-" + str(startIndex) + "-" + str(endIndex) + ".csv"


# %% define functions
def flattenJson(df):
    # get a list of columnHeadings
    columnHeadings = list(df)

    # loop through each columnHeading
    for columnHeading in columnHeadings:
        # if the df field has embedded json
        if "{" in df[df[columnHeading].notnull()][columnHeading].astype(str).str[0].values:
            # grab the data that is in brackets
            jsonBlob = df[columnHeading][df[columnHeading].astype(str).str[0] == "{"]
            # replace those values with nan
            df.loc[jsonBlob.index, columnHeading] = np.nan
            # turn jsonBlog to dataframe
            newDataFrame = jsonBlob.apply(pd.Series)
            newDataFrame = newDataFrame.add_prefix(columnHeading + '.')
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
    inputFilePathName = donorJsonDataFolder + "PHI-" + userID + ".json"
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
