#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: Anonymize and export Tidepool data
version: 0.0.2
created: 2018-05-22
author: Ed Nykaza
dependencies:
    * requires get-donor-data virtual environment (see readme for instructions)
    * requires Tidepool json data (e.g., PHI-jill-jellyfish.json)
    * requires commandline tool 'jq' for making the pretty json file
license: BSD-2-Clause
TODO:
* [] create a phi-jill-jellish-lite.xlsx
* [] first update this script with the new functinonailty
* [] then move them over to a module
* [] pull in jill-jellyfish.json dataset from AWS if no file is given
"""

# %% REQUIRED LIBRARIES
import pandas as pd
import datetime as dt
import numpy as np
import os
import sys
import shutil
import glob
import argparse
import hashlib
import pdb


# %% USER INPUTS
codeDescription = "Anonymize and export Tidepool data"

parser = argparse.ArgumentParser(description=codeDescription)

#parser.add_argument("-i",
#                    "--input-file-path",
#                    dest="inputFilePathAndName",
#                    default=os.path.join("..",
#                                         "example-data",
#                                         "PHI-jill-jellyfish.json"),
#                    help="path of .json data to be anonymized and exported")

parser.add_argument("-i",
                    "--input-tidepool-data",
                    dest="inputFilePathAndName",
                    default=os.path.join("..",
                                         "example-data",
                                         "PHI-jill-jellyfish-lite.json"),
                    help="a csv, xlsx, or json file that contains Tidepool data")


parser.add_argument("--data-field-list",
                    dest="dataFieldExportList",
                    default=os.path.join("..",
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
                    default=os.path.join("..",
                                         "example-data",
                                         "export", ""),
                    help="the path where the data is exported")

parser.add_argument("--output-format",
                    dest="exportFormat",
                    default="all",
                    help="the format of the exported data. Export options " +
                         "include json, xlsx, csv, csvs, or all")

parser.add_argument("--start-date",
                    dest="startDate",
                    default="2010-01-01",
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
            newDataFrame = pd.DataFrame(jsonBlob.tolist(),
                                        index=jsonBlob.index)
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

    return df


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

    if "payload.calibration_reading" in list(df):
        payloadCalReadingIndex = df["payload.calibration_reading"].notnull()

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
            scheduleNameDataFrame = df[df[scheduleName].notnull()].copy()
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


def filterAndSort(groupedDF, filterByField, sortByField):
    filterDF = groupedDF.get_group(filterByField).dropna(axis=1, how="all")
    filterDF = filterDF.sort_values(sortByField)
    return filterDF


def removeManufacturersFromAnnotationsCode(df):

    # remove manufacturer from annotations.code
    manufacturers = ["animas/",
                     "bayer/",
                     "carelink/",
                     "insulet/",
                     "medtronic/",
                     "tandem/"]

    annotationFields = [
        "annotations.code",
        "suppressed.annotations.code",
        "suppressed.suppressed.annotations.code"
        ]

    for annotationField in annotationFields:
        if annotationField in df.columns.values:
            if sum(df[annotationField].notnull()) > 0:
                df[annotationField] = \
                    df[annotationField].str. \
                    replace("|".join(manufacturers), "")

    return df


def mergeWizardWithBolus(df, csvExportFolder):

    if (("bolus" in set(df.type)) and ("wizard" in set(df.type))):
        bolusData = pd.read_csv(csvExportFolder + "bolus.csv",
                                low_memory=False)
        wizardData = pd.read_csv(csvExportFolder + "wizard.csv",
                                 low_memory=False)

        # remove manufacturer from annotations.code
        wizardData = removeManufacturersFromAnnotationsCode(wizardData)

        # merge the wizard data with the bolus data
        wizardData["calculatorId"] = wizardData["id"]
        wizardDataFields = [
            "bgInput",
            "bgTarget.high",
            "bgTarget.low",
            "bgTarget.range",
            "bgTarget.target",
            "bolus",
            "carbInput",
            "calculatorId",
            "insulinCarbRatio",
            "insulinOnBoard",
            "insulinSensitivity",
            "recommended.carb",
            "recommended.correction",
            "recommended.net",
            "units",
        ]
        keepTheseWizardFields = \
            set(wizardDataFields).intersection(list(wizardData))
        bolusData = pd.merge(bolusData,
                             wizardData[list(keepTheseWizardFields)],
                             how="left",
                             left_on="id",
                             right_on="bolus")

        mergedBolusData = bolusData.drop("bolus", axis=1)
    else:
        mergedBolusData = pd.DataFrame()

    return mergedBolusData


def hashUserId(userID, salt):

    usr_string = userID + salt
    hash_user = hashlib.sha256(usr_string.encode())
    hashID = hash_user.hexdigest()

    return hashID


def exportCsvFiles(df, exportFolder, fileName):
    csvExportFolder = os.path.join(exportFolder, "." + fileName + "-csvs", "")
    if not os.path.exists(csvExportFolder):
        os.makedirs(csvExportFolder)

    groupedData = df.groupby(by="type")
    for dataType in set(df[df.type.notnull()].type):
        csvData = filterAndSort(groupedData, dataType, "time")
        csvData.index.name = "jsonRowIndex"
        csvData.to_csv(csvExportFolder + dataType + ".csv")

    # merge wizard data with bolus data, and delete wizard data
    bolusWithWizardData = mergeWizardWithBolus(df, csvExportFolder)
    if len(bolusWithWizardData) > 0:
        bolusWithWizardData.to_csv(csvExportFolder + "bolus.csv", index=False)
    if os.path.exists(csvExportFolder + "wizard.csv"):
        os.remove(csvExportFolder + "wizard.csv")

    return csvExportFolder


def exportSingleCsv(df, exportFolder, fileName, csvExportFolder):
    # first load in all csv files
    csvFiles = glob.glob(csvExportFolder + "*.csv")
    bigTable = pd.DataFrame()
    for csvFile in csvFiles:
        bigTable = pd.concat([bigTable,
                              pd.read_csv(csvFile,
                                          low_memory=False,
                                          index_col="jsonRowIndex")])
    # then sort
    bigTable = bigTable.sort_values("time")
    bigTable.to_csv(os.path.join(exportFolder, fileName + ".csv"))

    return bigTable


def exportPrettyJson(df, exportFolder, fileName, csvExportFolder):

    # make a hidden file
    hiddenJsonFile = exportFolder + "." + fileName + ".json"
    df.to_json(hiddenJsonFile, orient='records')
    # make a pretty json file for export
    jsonExportFileName = exportFolder + fileName + ".json"
    os.system("jq '.' " + hiddenJsonFile + " > " + jsonExportFileName)
    # delete the hidden file
    os.remove(hiddenJsonFile)

    return


def exportExcelFile(csvExportFolder, exportFolder, fileName):
    writer = pd.ExcelWriter(exportFolder + fileName + ".xlsx")
    csvFiles = sorted(os.listdir(csvExportFolder))
    for csvFile in csvFiles:
        dataName = csvFile[:-4]
        tempCsvData = pd.read_csv(os.path.join(csvExportFolder,
                                               dataName + ".csv"),
                                  low_memory=False,
                                  index_col="jsonRowIndex")
        tempCsvData.to_excel(writer, dataName)
    writer.save()

    return


def readXlsxData(xlsxPathAndFileName):
    # load xlsx
    df = pd.read_excel(xlsxPathAndFileName, sheet_name=None, ignore_index=True)
    cdf = pd.concat(df.values(), ignore_index=True)
    cdf = cdf.set_index('jsonRowIndex')

    return cdf


def checkInputFile(inputFile):
    if os.path.isfile(inputFile):
        if os.stat(inputFile).st_size > 2:
            if inputFile[-4:] == "json":
                inputData = pd.read_json(inputFile, orient="records")
                fileName = os.path.split(inputFile)[-1][:-5]
            elif inputFile[-4:] == "xlsx":
                inputData = readXlsxData(inputFile)
                fileName = os.path.split(inputFile)[-1][:-5]
            elif inputFile[-3:] == "csv":
                inputData = pd.read_csv(inputFile, low_memory=False)
                fileName = os.path.split(inputFile)[-1][:-4]
            else:
                sys.exit("{0} is not a json, xlsx, or csv".format(inputFile))
        else:
            sys.exit("{0} contains too little data".format(inputFile))
    else:
        sys.exit("{0} does not exist".format(inputFile))

    # if fileName has PHI in it, remove PHI to get userID
    if "PHI" in fileName.upper():
        fileName = fileName[4:]

    return inputData, fileName


# %% GLOBAL VARIABLES

# check inputs and load data. File must be bigger than 1 KB, and in either
# json, xlsx, or csv format
data, userID = checkInputFile(args.inputFilePathAndName)

#pdb.set_trace()

## input folder(s)
#jsonFilePath = args.inputFilePathAndName
#if not os.path.isfile(jsonFilePath):
#    sys.exit("{0} is not a valid file path".format(jsonFilePath))
#
#allInstancesOfPHI = \
#    [i for i in range(len(jsonFilePath)) if jsonFilePath.startswith('PHI-', i)]
#
#phiUserId = jsonFilePath[max(allInstancesOfPHI):]
#if "PHI" not in phiUserId:
#    sys. exit("{0} must have PHI in the file name".format(phiUserId))
#
#userID = phiUserId[4:-5]

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
## load json file
#data = pd.read_json(jsonFilePath, orient="records")

# remove data between start and end dates
data = filterByDates(data, args.startDate, args.endDate)

# flatten embedded json, if it exists
data = flattenJson(data, requiredDataFields)

# only keep the data fields that are approved
data = filterByRequiredDataFields(data, requiredDataFields)

# %% clean up data
# remove negative durations
data = removeNegativeDurations(data)

# get rid of cgm values too low/high (< 38 & > 402 mg/dL)
data, numberOfInvalidCgmValues = removeInvalidCgmValues(data)

# Tslim calibration bug fix
data, numberOfTandemAndPayloadCalReadings = tslimCalibrationFix(data)

# % hash the required data fields
data = hashWithSalt(data, hashSaltFields, args.salt, userID)

# %% sort and export data
# sort data by time
data = data.sort_values("time")

# all of the exports are based off of csvs table, as they separate the
# bolus and wizard data
hashID = hashUserId(userID, args.salt)
csvExportFolder = exportCsvFiles(data, exportFolder, hashID)

if args.exportFormat in ["csv", "json", "all"]:
    allData = exportSingleCsv(data, exportFolder, hashID, csvExportFolder)

if args.exportFormat in ["json", "all"]:
    exportPrettyJson(allData, exportFolder, hashID, csvExportFolder)

if args.exportFormat in ["xlsx", "all"]:
    exportExcelFile(csvExportFolder, exportFolder, hashID)

if args.exportFormat in ["csvs", "all"]:
    # unhide the csv files
    unhiddenCsvExportFolder = \
        os.path.join(exportFolder, hashID + "-csvs", "")
    os.rename(csvExportFolder, unhiddenCsvExportFolder)
else:
    shutil.rmtree(csvExportFolder)