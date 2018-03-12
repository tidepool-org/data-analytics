#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: Anonymize and export Tidepool data
version: 0.0.1
created: 2018-02-21
author: Ed Nykaza
dependencies:
    * requires get-donor-data virtual environment (see readme for instructions)
license: BSD-2-Clause
TODO:
* [] move code that is used by multiple scripts to a utility folder/library
* [] make sure that jq library is added to the virtual environment
* []
"""

# %% REQUIRED LIBRARIES
import pandas as pd
import datetime as dt
import numpy as np
import os
import sys
import argparse
import hashlib


# %% USER INPUTS
codeDescription = "Anonymize and export Tidepool data"

parser = argparse.ArgumentParser(description=codeDescription)

parser.add_argument("-i",
                    "--input-file-path",
                    dest="inputPath",
                    default=os.path.join(".",
                                         "example-data",
                                         "PHI-jill-jellyfish.json"),
                    help="path of .json data to be anonymized and exported")

parser.add_argument("--data-field-list",
                    dest="dataFieldExportList",
                    default=os.path.join(".",
                                         "example-data",
                                         "dataFieldExportList.csv"),
                    help="a csv file that contains a list of fields to export")

parser.add_argument("--salt",
                    dest="salt",
                    default="no salt specified",
                    help="salt used in the hashing algorithm")

parser.add_argument("-o",
                    "--output-data-path",
                    dest="exportPath",
                    default=os.path.join(".", "example-data", "export", ""),
                    help="the path where the data is exported")

parser.add_argument("--output-format",
                    dest="exportFormat",
                    default="json",
                    help="the format of the exported data")


parser.add_argument("--start-date",
                    dest="startDate",
                    default="1900-01-01",
                    help="filter data by startDate and EndDate")

parser.add_argument("--end-date",
                    dest="endDate",
                    default=dt.datetime.now().strftime("%Y-%m-%d"),
                    help="filter data by startDate and EndDate")

args = parser.parse_args()


# %% FUNCTIONS
def filterByDates(df, startDate, endDate):

    # filter by qualified start & end date, and sort
    df = \
        df[(df.time >= startDate) &
           (df.time <= (endDate + "T23:59:59"))]

    return df


def filterByRequiredDataFields(df, requiredDataFields):

    dfExport = pd.DataFrame()
    for fIndex in range(0, len(requiredDataFields)):
        if requiredDataFields[fIndex] in df.columns.values:
            dfExport = pd.concat([dfExport, df[requiredDataFields[fIndex]]],
                                 axis=1)

    return dfExport


def tempRemoveFields(df):
    removeFields = ["basalSchedules",
                    "bgTarget",
                    "bgTargets",
                    "carbRatio",
                    "carbRatios",
                    "insulinSensitivity",
                    "insulinSensitivities"]

    tempRemoveFields = list(set(df) & set(removeFields))
    tempDf = df[tempRemoveFields]
    df = df.drop(columns=tempRemoveFields)

    return df, tempDf


def flattenJson(df, requiredDataFields):

    # remove fields that we don't want to flatten
    df, holdData = tempRemoveFields(df)

    # remove [] from annotations field
    df = removeBrackets(df, "annotations")

    # get a list of data types of column headings
    columnHeadings = list(df)  # ["payload", "suppressed"]

    # loop through each columnHeading
    for colHead in columnHeadings:
        # if the df field has embedded json
        if "{" in df[df[colHead].notnull()][colHead].astype(str).str[0].values:
            # grab the data that is in brackets
            jsonBlob = df[colHead][df[colHead].astype(str).str[0] == "{"]

            # replace those values with nan
            df.loc[jsonBlob.index, colHead] = np.nan

            # turn jsonBlog to dataframe
            newDataFrame = pd.DataFrame(jsonBlob.tolist())
            newDataFrame = newDataFrame.add_prefix(colHead + '.')
            newColHeadings = list(newDataFrame)

            # put df back into the main dataframe
            for newColHeading in list(set(newColHeadings) &
                                      set(requiredDataFields)):
                tempDataFrame = newDataFrame[newColHeading]
                df = pd.concat([df, tempDataFrame], axis=1)

    # add the fields that were removed back in
    df = pd.concat([df, holdData], axis=1)

    return df


def removeBrackets(df, fieldName):
    if fieldName in list(df):
        df.loc[df[fieldName].notnull(), fieldName] = \
            df.loc[df[fieldName].notnull(), fieldName].str[0]

    return df


def removeNegativeDurations(df):
    if "duration" in list(df):
        nNegativeDurations = sum(df.duration < 0)
        if nNegativeDurations > 0:
            df = df[~(df.duration < 0)]

    return df, nNegativeDurations


def removeInvalidCgmValues(df):

    nBefore = len(df)
    # remove values < 38 and > 402 mg/dL
    df = df.drop(df[((df.type == "cbg") &
                     (df.value < 2.109284236597303))].index)
    df = df.drop(df[((df.type == "cbg") &
                     (df.value > 22.314006924003046))].index)
    nRemoved = nBefore - len(df)

    return df, nRemoved


def tslimCalibrationFix(df):
    searchfor = ['tan']
    tandemDataIndex = ((df.deviceId.str.contains('|'.join(searchfor))) &
                       (df.type == "deviceEvent"))
#    nTandemData = sum(tandemDataIndex)

    if "payload.calibration_reading" in list(df):
        payloadCalReadingIndex = df["payload.calibration_reading"].notnull()
#        nPayloadCalReadings = sum(payloadCalReadingIndex)

        nTandemAndPayloadCalReadings = sum(tandemDataIndex &
                                           payloadCalReadingIndex)

        if nTandemAndPayloadCalReadings > 0:
            # if reading is > 30 then it is in the wrong units
            if df["payload.calibration_reading"].min() > 30:
                df.loc[payloadCalReadingIndex, "value"] = \
                    df[tandemDataIndex & payloadCalReadingIndex] \
                    ["payload.calibration_reading"] / 18.01559
            else:
                df.loc[payloadCalReadingIndex, "value"] = \
                    df[tandemDataIndex &
                        payloadCalReadingIndex]["payload.calibration_reading"]
    else:
        nTandemAndPayloadCalReadings = 0
    return df, nTandemAndPayloadCalReadings


def hashScheduleNames(df, salt, userID):

    scheduleNames = ["basalSchedules",
                     "bgTargets",
                     "carbRatios",
                     "insulinSensitivities"]

    # loop through each of the scheduleNames that exist
    for scheduleName in scheduleNames:
        # if scheduleName exists, find the rows that have the scheduleName
        if scheduleName in list(df):
            scheduleNameDataFrame = df[df[scheduleName].notnull()]
            scheduleNameRows = scheduleNameDataFrame[scheduleName].index
            # loop through each schedule name row
            uniqueScheduleNames = []
            for scheduleNameRow in scheduleNameRows:
                scheduleNameKeys = list(scheduleNameDataFrame[scheduleName]
                                        [scheduleNameRow].keys())
                uniqueScheduleNames = list(set(uniqueScheduleNames +
                                               scheduleNameKeys))
            # loop through each unique schedule name and create a hash
            for uniqueScheduleName in uniqueScheduleNames:
                hashedScheduleName = \
                    hashlib.sha256((uniqueScheduleName + args.salt + userID).
                                   encode()).hexdigest()[0:8]
                # find and replace those names in the json blob
                scheduleNameDataFrame.loc[:, scheduleName] = \
                    scheduleNameDataFrame[scheduleName] \
                    .astype(str).str.replace(uniqueScheduleName,
                                             hashedScheduleName)

            # drop and reattach the new data
            df = df.drop(columns=scheduleName)
            df = pd.merge(df, scheduleNameDataFrame.loc[:, ["time",
                                                            scheduleName]],
                          how="left", on="time")
    return df


def hashData(df, columnHeading, lengthOfHash, salt, userID):

    df[columnHeading] = \
        (df[columnHeading].astype(str) + salt + userID).apply(
        lambda s: hashlib.sha256(s.encode()).hexdigest()[0:lengthOfHash])

    return df


def hashWithSalt(df, hashSaltFields, salt, userID):

    for hashSaltField in hashSaltFields:
        if hashSaltField in df.columns.values:
            df.loc[df[hashSaltField].notnull(), hashSaltField] = \
                hashData(pd.DataFrame(df.loc[df[hashSaltField].notnull(),
                                             hashSaltField]),
                         hashSaltField, 8, salt, userID)

    # also hash the schedule names
    df = hashScheduleNames(df, salt, userID)

    return df


def exportPrettyJson(df, exportFolder, fileName):
    # make a hidden file
    hiddenJsonFile = exportFolder + "." + fileName + ".json"
    df.to_json(hiddenJsonFile, orient='records')
    # make a pretty json file for export
    jsonExportFileName = exportFolder + fileName + ".json"
    os.system("jq '.' " + hiddenJsonFile + " > " + jsonExportFileName)
    # delete the hidden file
    os.remove(hiddenJsonFile)

    return


def filterAndSort(groupedDF, filterByField, sortByField):
    filterDF = groupedDF.get_group(filterByField).dropna(axis=1, how="all")
    filterDF = filterDF.sort_values(sortByField)
    return filterDF


def exportCsvFiles(df, exportFolder, fileName):
    csvExportFolder = os.path.join(exportFolder, fileName + "-csvs", "")
    if not os.path.exists(csvExportFolder):
        os.makedirs(csvExportFolder)

    groupedData = df.groupby(by="type")
    for dataType in set(df[df.type.notnull()].type):
        csvData = filterAndSort(groupedData, dataType, "time")
        csvData.index.name = "jsonRowIndex"
        csvData.to_csv(csvExportFolder + dataType + ".csv")

    return


# %% GLOBAL VARIABLES
# input folder(s)
jsonFilePath = args.inputPath
if not os.path.isfile(jsonFilePath):
    sys.exit("{0} is not a valid file path".format(jsonFilePath))

userID = jsonFilePath[
        (jsonFilePath.find("PHI-") + 4):
        (jsonFilePath.find(".json"))]

dataFieldPath = args.dataFieldExportList
if not os.path.isfile(dataFieldPath):
    sys.exit("{0} is not a valid file path".format(dataFieldPath))

# create output folder(s)
exportFolder = args.exportPath
if not os.path.exists(exportFolder):
    os.makedirs(exportFolder)

dataFieldExportList = pd.read_csv(dataFieldPath)
requiredDataFields = \
    list(dataFieldExportList.loc[dataFieldExportList.include.fillna(False),
                                 "dataFieldList"])

hashSaltFields = list(dataFieldExportList.loc[
        dataFieldExportList.hashNeeded.fillna(False), "dataFieldList"])


# %% START OF CODE
# load json file
data = pd.read_json(jsonFilePath, orient="records")

# remove data between start and end dates
data = filterByDates(data, args.startDate, args.endDate)

# flatten embedded json, if it exists
data = flattenJson(data, requiredDataFields)

# only keep the data fields that are approved
data = filterByRequiredDataFields(data, requiredDataFields)

# %% clean up data
# remove negative durations
data, numberOfNegativeDurations = removeNegativeDurations(data)

# get rid of cgm values too low/high (< 38 & > 402 mg/dL)
data, numberOfInvalidCgmValues = removeInvalidCgmValues(data)

# Tslim calibration bug fix
data, numberOfTandemAndPayloadCalReadings = tslimCalibrationFix(data)

# %% hash the required data/fields
data = hashWithSalt(data, hashSaltFields, args.salt, userID)

# %% sort and save data
# sort data by time
data = data.sort_values("time")

if args.exportFormat in ["json", "all"]:
    exportPrettyJson(data, exportFolder, userID)

if args.exportFormat in ["csv", "xlsx", "all"]:
    exportCsvFiles(data, exportFolder, userID)









































