#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: Anonymize and export Tidepool data
version: 0.0.2
created: 2018-05-22
author: Ed Nykaza
dependencies:
    * requires tidepool-data-env (see readme for instructions)
    * requires Tidepool data (e.g., PHI-jill-jellyfish.json)
    * requires commandline tool 'jq' for making the pretty json file
license: BSD-2-Clause
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
import ast


# %% USER INPUTS
codeDescription = "Anonymize and export Tidepool data"

parser = argparse.ArgumentParser(description=codeDescription)

parser.add_argument("-i",
                    "--input-tidepool-data",
                    dest="inputFilePathAndName",
                    default=os.path.join("..",
                                         "example-data",
                                         "PHI-jill-jellyfish-lite.json"),
                    help="csv, xlsx, or json file that contains Tidepool data")

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

parser.add_argument("--merge-wizard-data",
                    dest="mergeWizardDataWithBolusData",
                    default=True,
                    help="option to merge wizard data with bolus data, " +
                         "default, is true")

parser.add_argument("--output-format",
                    dest="exportFormat",
                    default=["all"],
                    help="the format of the exported data. Export options " +
                         "include json, xlsx, csv, csvs, or all" +
                         "NOTE: you can include multiple formats in a " +
                         "list (e.g., ['json', 'csv'])")

parser.add_argument("--start-date",
                    dest="startDate",
                    default="2010-01-01",
                    help="filter data by startDate and EndDate")

parser.add_argument("--end-date",
                    dest="endDate",
                    default=dt.datetime.now().strftime("%Y-%m-%d"),
                    help="filter data by startDate and EndDate")

parser.add_argument("--filterByDatesExceptUploadsAndSettings",
                    dest="filterByDatesExceptUploadsAndSettings",
                    default=True,
                    help="upload and settings data can occur before and " +
                         "after start and end dates, so include ALL " +
                         "upload and settings data in export")

args = parser.parse_args()


# %% LOAD DATA FUNCTIONS
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


# %% FILTER DATA FUNCTIONS
def checkDataFieldList(dataFieldPath):
    if not os.path.isfile(dataFieldPath):
        sys.exit("{0} is not a valid file path".format(dataFieldPath))

    dataFieldExportList = pd.read_csv(dataFieldPath)
    approvedDataFields = \
        list(dataFieldExportList.loc[dataFieldExportList.include.fillna(False),
                                     "dataFieldList"])

    hashSaltFields = list(dataFieldExportList.loc[
            dataFieldExportList.hashNeeded.fillna(False), "dataFieldList"])

    return approvedDataFields, hashSaltFields


def filterByDates(df, startDate, endDate):

    # filter by qualified start & end date, and sort
    df = \
        df[(df.time >= startDate) &
           (df.time <= (endDate + "T23:59:59"))]

    return df


def filterByDatesExceptUploadsAndSettings(df, startDate, endDate):

    # filter by qualified start & end date, and sort
    uploadEventsSettings = df[((df.type == "upload") |
                               (df.type == "deviceEvent") |
                               (df.type == "cgmSettings") |
                               (df.type == "pumpSettings"))]

    theRest = df[~((df.type == "upload") |
                 (df.type == "deviceEvent") |
                 (df.type == "cgmSettings") |
                 (df.type == "pumpSettings"))]

    if "est.localTime" in list(df):

        theRest = theRest[(theRest["est.localTime"] >= startDate) &
                          (theRest["est.localTime"] <=
                           (endDate + "T23:59:59"))]
    else:
        theRest = theRest[(theRest["time"] >= startDate) &
                          (theRest["time"] <= (endDate + "T23:59:59"))]

    df = pd.concat([uploadEventsSettings, theRest])

    return df


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


def removeBrackets(df, fieldName):
    if fieldName in list(df):
        df.loc[df[fieldName].notnull(), fieldName] = \
            df.loc[df[fieldName].notnull(), fieldName].str[0]

    return df


def flattenJson(df, dataFieldsForExport):

    # remove fields that we don't want to flatten
    df, holdData = tempRemoveFields(df)

    # remove [] from annotations field
    df = removeBrackets(df, "annotations")

    # get a list of data types of column headings
    columnHeadings = list(df)  # ["payload", "suppressed"]

    # loop through each columnHeading
    newDataFrame = pd.DataFrame()

    for colHead in columnHeadings:
        # if the df field has embedded json
        if any(isinstance(item, dict) for item in df[colHead]):
            # grab the data that is in brackets
            jsonBlob = df[colHead][df[colHead].astype(str).str[0] == "{"]

            # replace those values with nan
            df.loc[jsonBlob.index, colHead] = np.nan

            # turn jsonBlob to dataframe
            newDataFrame = pd.concat([newDataFrame, pd.DataFrame(jsonBlob.tolist(),
                                        index=jsonBlob.index).add_prefix(colHead + '.')], axis=1)

    newColHeadings = list(newDataFrame)

    # put df back into the main dataframe
    columnFilter = list(set(newColHeadings) & set(dataFieldsForExport))
    tempDataFrame = newDataFrame.filter(items=columnFilter)
    df = pd.concat([df, tempDataFrame], axis=1)

    # add the fields that were removed back in
    df = pd.concat([df, holdData], axis=1)

    return df


def filterByApprovedDataFields(df, dataFieldsForExport):

    # flatten embedded json, if it exists
    df = flattenJson(df, dataFieldsForExport)

    dfExport = pd.DataFrame()
    colHeadings = list(df)
    columnFilter = list(set(colHeadings) & set(dataFieldsForExport))
    dfExport = df.filter(items=columnFilter)

    return dfExport


# %% CLEAN DATA FUNCTIONS
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


# %% ANONYMIZE DATA FUNCTIONS
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
                # TODO: come up with a better work around
                # work-around if input file is json vs. csv format
                try: # this is the json version
                    scheduleNameKeys = \
                        list(scheduleNameDataFrame[scheduleName]
                        [scheduleNameRow].keys())
                except: # this is the csv version
                    scheduleNameKeys = \
                        list(ast.literal_eval(scheduleNameDataFrame[scheduleName]
                        [scheduleNameRow]).keys())

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
            df = pd.merge(df,
                          scheduleNameDataFrame.loc[:,
                                                    ["time", scheduleName]],
                                                    how="left", on="time")
    return df


def hashData(df, columnHeading, lengthOfHash, salt, userID):

    df[columnHeading] = \
        (df[columnHeading].astype(str) + salt + userID).apply(
        lambda s: hashlib.sha256(s.encode()).hexdigest()[0:lengthOfHash])

    return df


def anonymizeData(df, hashSaltFields, salt, userID):

    for hashSaltField in hashSaltFields:
        if hashSaltField in df.columns.values:
            df.loc[df[hashSaltField].notnull(), hashSaltField] = \
                hashData(pd.DataFrame(df.loc[df[hashSaltField].notnull(),
                                             hashSaltField]),
                         hashSaltField, 8, salt, userID)

    # also hash the schedule names
    df = hashScheduleNames(df, salt, userID)

    return df


def hashUserId(userID, salt):

    usr_string = userID + salt
    hash_user = hashlib.sha256(usr_string.encode())
    hashID = hash_user.hexdigest()

    return hashID


# %% EXPORT DATA FUNCTIONS
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


def mergeWizardWithBolus(df, exportDirectory):

    if (("bolus" in set(df.type)) and ("wizard" in set(df.type))):
        bolusData = pd.read_csv(exportDirectory + "bolus.csv",
                                low_memory=False)
        wizardData = pd.read_csv(exportDirectory + "wizard.csv",
                                 low_memory=False)



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


def cleanDiretory(exportFolder, fileName):

    # if there is a failure during an export, you will want to clear out
    # the remnants before trying to export again, so delete files if they exist
    hiddenCsvExportFolder = os.path.join(exportFolder,
                                         "." + fileName + "-csvs", "")
    if os.path.exists(hiddenCsvExportFolder):
        shutil.rmtree(hiddenCsvExportFolder)

    os.makedirs(hiddenCsvExportFolder)

    unhiddenCsvExportFolder = os.path.join(exportFolder,
                                           fileName + "-csvs", "")

    for fType in ["xlsx", "json", "csv"]:
        fName = os.path.join(exportFolder, fileName + "." + fType)
        if os.path.exists(fName):
            os.remove(fName)

    # if unhiddenCsvExportFolder folder exists, delete it
    if os.path.exists(unhiddenCsvExportFolder):
        shutil.rmtree(unhiddenCsvExportFolder)

    return hiddenCsvExportFolder


def exportCsvFiles(df, exportFolder, fileName, mergeCalculatorData):
    hiddenCsvExportFolder = cleanDiretory(exportFolder, fileName)

    groupedData = df.groupby(by="type")
    for dataType in set(df[df.type.notnull()].type):
        csvData = filterAndSort(groupedData, dataType, "time")
        csvData.index.name = "jsonRowIndex"
        csvData.to_csv(hiddenCsvExportFolder + dataType + ".csv")

    # merge wizard data with bolus data, and delete wizard data
    if mergeCalculatorData:
        bolusWithWizardData = mergeWizardWithBolus(df, hiddenCsvExportFolder)
        if len(bolusWithWizardData) > 0:
            bolusWithWizardData.to_csv(hiddenCsvExportFolder + "bolus.csv",
                                       index=False)
        if os.path.exists(hiddenCsvExportFolder + "wizard.csv"):
            os.remove(hiddenCsvExportFolder + "wizard.csv")

    return hiddenCsvExportFolder


def exportSingleCsv(df, exportFolder, fileName, exportDirectory, fileType):
    # first load in all csv files
    csvFiles = glob.glob(exportDirectory + "*.csv")
    bigTable = pd.DataFrame()
    for csvFile in csvFiles:
        bigTable = \
            pd.concat([bigTable, pd.read_csv(csvFile, low_memory=False,
                      index_col="jsonRowIndex")], sort=False)

    # then sort
    bigTable = bigTable.sort_values("time")
    if "csv" in fileType:
        bigTable.to_csv(os.path.join(exportFolder, fileName + ".csv"))

    return bigTable


def exportPrettyJson(df, exportFolder, fileName, exportDirectory):
    # make a hidden file
    hiddenJsonFile = exportFolder + "." + fileName + ".json"
    df.to_json(hiddenJsonFile, orient='records')
    # make a pretty json file for export
    jsonExportFileName = exportFolder + fileName + ".json"
    # export pretty and remove nulls
    os.system("jq 'del(.[][] | nulls)' " +
              hiddenJsonFile + " > " + jsonExportFileName)
    # delete the hidden file
    os.remove(hiddenJsonFile)

    return


def exportExcelFile(exportDirectory, exportFolder, fileName):
    mylen = np.vectorize(len)
    writer = pd.ExcelWriter(exportFolder + fileName + ".xlsx",
                            engine='xlsxwriter')

    workbook = writer.book
    header_format = workbook.add_format({'bold': True,
                                         'valign': 'center',
                                         'border': False,
                                         'align': 'center'})

    cell_format = workbook.add_format({'align': 'center'})

    csvFiles = sorted(os.listdir(exportDirectory))
    for csvFile in csvFiles:
        dataName = csvFile[:-4]

        tempCsvData = pd.read_csv(
                os.path.join(exportDirectory, dataName + ".csv"),
                low_memory=False)

        # put the date time columns in an excel interpretable format
        for col_heading in list(tempCsvData):
            if "time" in col_heading.lower()[-4:]:
                tempCsvData[col_heading] = \
                    pd.to_datetime(tempCsvData[col_heading])

        tempCsvData.to_excel(writer, dataName, startrow=1, header=False,
                             index=False, freeze_panes=(1, 1))

        worksheet = writer.sheets[dataName]
        workbook.add_format({'align': 'center'})

        # Write the column headers with the defined format
        for col_num, value in enumerate(tempCsvData.columns.values):
            worksheet.write(0, col_num, value, header_format)
            colWidth = max(len(value),
                           max(mylen(tempCsvData.iloc[:, col_num].astype(str))))
            worksheet.set_column(col_num, col_num, colWidth, cell_format)

    writer.save()

    return


def readXlsxData(xlsxPathAndFileName):
    # load xlsx
    df = pd.read_excel(xlsxPathAndFileName, sheet_name=None, ignore_index=True)
    cdf = pd.concat(df.values(), ignore_index=True)
    cdf = cdf.set_index('jsonRowIndex')

    return cdf


def exportData(df, fileName, fileType, exportDirectory, mergeCalculatorData):
    # create output folder(s)
    if not os.path.exists(exportDirectory):
        os.makedirs(exportDirectory)

    # sort data by time
    df = df.sort_values("time")

    # all of the exports are based off of csvs table, which are needed to
    # merge the bolus and wizard (AKA calculator) data
    csvExportFolder = exportCsvFiles(df, exportDirectory,
                                     fileName, mergeCalculatorData)

    if (("csv" in fileType) | ("json" in fileType) | ("all" in fileType)):
        allData = exportSingleCsv(df, exportDirectory,
                                  fileName, csvExportFolder, fileType)

    if (("json" in fileType) | ("all" in fileType)):
        exportPrettyJson(allData, exportDirectory, fileName, csvExportFolder)

    if (("xlsx" in fileType) | ("all" in fileType)):
        exportExcelFile(csvExportFolder, exportDirectory, fileName)

    if (("csvs" in fileType) | ("all" in fileType)):
        # unhide the csv files
        unhiddenCsvExportFolder = \
            os.path.join(exportDirectory, fileName + "-csvs", "")
        os.rename(csvExportFolder, unhiddenCsvExportFolder)
    else:
        shutil.rmtree(csvExportFolder)

    return


# %% LOAD DATA
# check input file and load data. File must be bigger than 2 bytes,
# and in either json, xlsx, or csv format
data, userID = checkInputFile(args.inputFilePathAndName)


# %% FILTER DATA
# check export/approved data field list
outputFields, anonymizeFields = checkDataFieldList(args.dataFieldExportList)

# remove data between start and end dates
if args.filterByDatesExceptUploadsAndSettings:
    data = filterByDatesExceptUploadsAndSettings(data,
                                                 args.startDate,
                                                 args.endDate)
else:
    data = filterByDates(data, args.startDate, args.endDate)

# only keep the data fields that are approved
data = filterByApprovedDataFields(data, outputFields)


# %% CLEAN DATA
# remove negative durations
data = removeNegativeDurations(data)

# get rid of cgm values too low/high (< 38 & > 402 mg/dL)
data, numberOfInvalidCgmValues = removeInvalidCgmValues(data)

# Tslim calibration bug fix
data, numberOfTandemAndPayloadCalReadings = tslimCalibrationFix(data)


# %% ANONYMIZE DATA

# remove manufacturer from annotations.code
data = removeManufacturersFromAnnotationsCode(data)

# hash the required data fields
data = anonymizeData(data, anonymizeFields, args.salt, userID)
hashID = hashUserId(userID, args.salt)


# %% EXPORT DATA
# if a hashID is defined, then use the hashID, if not use the PHI userID
if 'hashID' in locals():
    outputName = hashID
else:
    outputName = "PHI-" + userID

exportData(data, outputName, args.exportFormat,
           args.exportPath, args.mergeWizardDataWithBolusData)
