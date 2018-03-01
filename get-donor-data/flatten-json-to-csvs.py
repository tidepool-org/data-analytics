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
* [] Make sure that .0 column headers do not exist
* [] Add a check if the data was already processed, not to process
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
startIndex = 0
endIndex = 2334

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

metadataFilePathName = donorFolder + phiDateStamp + \
    "-donorMetadata-" + str(startIndex) + "-" + str(endIndex) + ".csv"

# load in list of unique donors
uniqueDonors = pd.read_csv(donorFolder + phiDateStamp + "-uniqueDonorList.csv",
                           index_col="dIndex")

allDiagnostics = pd.DataFrame()


# %% define functions
def removeZeroFields(df):

    # if *.0 exists then map back to proper field name
    zeroFields = [
            "duration.0",
            "insulinSensitivity.0",
            "units.0"
            ]

    for zeroField in zeroFields:
        if zeroField in list(df):
            print("zeroFields still exist")
            break
#            df[zeroField.replace(".0", "")] = df[zeroField]

    return df


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

            # make sure that the df does not already exist in the dataset
            for newColHeading in newColHeadings:
                if newColHeading in list(df):
                    print("has a column that already exists")
                    break
                    # pop the original df out of the dataset
                    tempData2 = pd.DataFrame(df.pop(newColHeading))

                    # combine the columns that have the same column heading
                    tempDataFrame = pd.concat([
                        tempData2[tempData2[newColHeading].notnull()][newColHeading],
                        newDataFrame[newColHeading]])

                else:
                    tempDataFrame = newDataFrame[newColHeading]

                # put df back into the main dataframe
                df = pd.concat([df, tempDataFrame], axis=1)

                # if *.0 exists then map back to proper field name
                df = removeZeroFields(df)

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

    print(dIndex, "of", uniqueDonors.index.max())

    allDiagnostics = pd.concat([allDiagnostics, diagnostics])

# %% save output
uniqueDonors = pd.merge(uniqueDonors,
                        allDiagnostics,
                        how="left",
                        on="userID")

uniqueDonors.index.name = "dIndex"
uniqueDonors.to_csv(metadataFilePathName)
