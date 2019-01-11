#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: get users settings and events
version: 0.0.1
created: 2019-01-11
author: Ed Nykaza
dependencies:
    *
license: BSD-2-Clause
"""


# %% REQUIRED LIBRARIES
import pandas as pd
import datetime as dt
import numpy as np
import tidals as td
import os
import sys
import shutil
import glob
import argparse
import hashlib
import ast
import time
import pdb


# %% USER INPUTS (ADD THIS IN LATER)
#codeDescription = "Get user's settings and events"
#parser = argparse.ArgumentParser(description=codeDescription)


# %% FUNCTIONS

dataFieldExportList = [
        'activeSchedule', 'alarmType', 'annotations.code', 'annotations.threshold',
        'annotations.value', 'basalSchedules', 'bgInput', 'bgTarget', 'bgTarget.high', 'bgTarget.low',
        'bgTarget.range', 'bgTarget.start', 'bgTarget.target', 'bgTargets', 'bolus', 'carbInput',
        'carbRatio', 'carbRatios', 'carbRatio.amount', 'carbRatio.start', 'change.agent',
        'change.from', 'change.to', 'clockDriftOffset', 'computerTime', 'conversionOffset',
        'deliveryType', 'deviceId', 'deviceManufacturers', 'deviceModel', 'deviceSerialNumber',
        'deviceTags', 'deviceTime', 'duration', 'expectedDuration', 'expectedExtended',
        'expectedNormal', 'extended', 'highAlerts.enabled', 'highAlerts.level',
        'highAlerts.snooze', 'id', 'insulinCarbRatio', 'insulinOnBoard', 'insulinSensitivity',
        'insulinSensitivity.amount', 'insulinSensitivity.start', 'insulinSensitivities',
        'lowAlerts.enabled', 'lowAlerts.level', 'lowAlerts.snooze', 'normal',
        'outOfRangeAlerts.enabled', 'outOfRangeAlerts.snooze',
        'payload.calibration_reading', 'payload.Status', 'payload.Trend Arrow',
        'payload.Trend Rate', 'percent', 'primeTarget', 'rate', 'rateOfChangeAlerts.fallRate.enabled',
        'rateOfChangeAlerts.fallRate.rate', 'rateOfChangeAlerts.riseRate.enabled',
        'rateOfChangeAlerts.riseRate.rate', 'reason.resumed', 'reason.suspended', 'recommended.carb',
        'recommended.correction', 'recommended.net', 'scheduleName', 'status', 'subType',
        'time', 'timeProcessing', 'timezone', 'timezoneOffset', 'transmitterId', 'type', 'units',
        'units.bg', 'units.carb', 'uploadId', 'value', 'version'
]

# CLEAN DATA FUNCTIONS
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


# OTHER
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
    # and add the fields that were removed back in
    columnFilter = list(set(newColHeadings) & set(dataFieldsForExport))
    tempDataFrame = newDataFrame.filter(items=columnFilter)
    df = pd.concat([df, tempDataFrame, holdData], axis=1)

    return df


def mergeWizardWithBolus(df):

    if "wizard" in data["type"].unique():
        bolusData = data[data.type == "bolus"].copy().dropna(axis=1, how="all")
        wizardData = data[data.type == "wizard"].copy().dropna(axis=1, how="all")

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


def addUploadDate(df):
    uploadTimes = pd.DataFrame(df[df.type == "upload"].groupby("uploadId").time.describe()["top"])
    uploadTimes.reset_index(inplace=True)
    uploadTimes.rename(columns={"top": "uploadTime"}, inplace=True)
    df = pd.merge(df, uploadTimes, how='left', on='uploadId')
    df["uploadTime"] = pd.to_datetime(df["uploadTime"])

    return df


def mmolL_to_mgdL(mmolL):
    return mmolL * 18.01559


# %% LOAD IN ONE FILE, BUT EVENTUALLY THIS WILL LOOOP THROUGH ALL USER'S
dataPulledDate = "2018-09-28"
phiDate = "PHI-" + dataPulledDate
donorPath = os.path.join("..", "bigdata-processing-pipeline", "data", phiDate + "-donor-data")

donorList = phiDate + "-uniqueDonorList.csv"
donors = td.load.load_csv(os.path.join(donorPath, donorList))

# this is where the loop will go:
dIndex = 2379

# %% ID, HASHID, AGE, & YLW
userID = donors.userID[dIndex]
hashID = donors.hashID[dIndex]
bDate = pd.to_datetime(donors.bDay[dIndex][0:7])
dDate = pd.to_datetime(donors.dDay[dIndex][0:7])


# %% LOAD IN DONOR JSON DATA
metadata = pd.DataFrame(index=[dIndex])
jsonDataPath = os.path.join(donorPath, phiDate + "-donorJsonData")
jsonFileName = os.path.join(jsonDataPath, "PHI-" + userID + ".json")

if os.path.exists(jsonFileName):
    fileSize = os.stat(jsonFileName).st_size
    metadata["fileSizeKB"] = fileSize / 1000
    if fileSize > 1000:
        data = td.load.load_json(jsonFileName)
        # sort the data by time
        data.sort_values("time", inplace=True)

        # flatten the embedded json
        data = flattenJson(data, dataFieldExportList)



# %% CLEAN DATA
        # remove negative durations
        data, nNegativeDurations = removeNegativeDurations(data)
        metadata["nNegativeDurations"] = nNegativeDurations

        # get rid of cgm values too low/high (< 38 & > 402 mg/dL)
        data, nInvalidCgmValues = removeInvalidCgmValues(data)
        metadata["nInvalidCgmValues"] = nInvalidCgmValues

        # Tslim calibration bug fix
        data, nTandemAndPayloadCalReadings = tslimCalibrationFix(data)
        metadata["nTandemAndPayloadCalReadings"] = nTandemAndPayloadCalReadings


# %% ADD UPLOAD DATE
        # attach upload time to each record, for resolving duplicates
        if "upload" in data.type.unique():
            data = addUploadDate(data)


# %% TIME (UTC, TIMEZONE, DAY AND EVENTUALLY LOCAL TIME)
            data["utcTime"] = pd.to_datetime(data["time"])
            data["timezone"].fillna(method='ffill', inplace=True)
            data["timezone"].fillna(method='bfill', inplace=True)
            data["day"] = pd.DatetimeIndex(data["utcTime"]).date

# %% ID, HASHID, AGE, & YLW
            data["userID"] = userID
            data["hashID"] = hashID
            data["age"] = np.floor((data["utcTime"] - bDate).dt.days/365.25).astype(int)
            data["ylw"] = np.floor((data["utcTime"] - dDate).dt.days/365.25).astype(int)


# %% FORMAT BOLUS DATA
            bolus = mergeWizardWithBolus(data)
            if len(bolus) > 0:
                # get rid of duplicates that have the same ["time", "normal"]
                bolus, nBolusDuplicatesRemoved = \
                    td.clean.remove_duplicates(bolus, bolus[["time", "normal"]])
                metadata["nBolusDuplicatesRemoved"] = nBolusDuplicatesRemoved


# %% ISF, CIR
                if "insulinSensitivities" in list(bolus):
                    pdb.set_trace()

                # ISF
                bolus["isf_mmolL_U"] = bolus["insulinSensitivity"]
                bolus["isf"] = mmolL_to_mgdL(bolus["isf_mmolL_U"])
                isf = bolus.loc[bolus["isf"].notnull(), ["utcTime", "isf", "isf_mmolL_U"]]

                # CIR
                cir = bolus.loc[bolus["insulinCarbRatio"].notnull(), ["utcTime", "insulinCarbRatio"]]



# %% INSULIN ACTIVITY DURATION


# %% MAX BASAL RATE


# %% MAX BOLUS AMOUNT


# %% CORRECTION TARGET


# %% BASAL RATES (TIME, VALUE, DURATION, TYPE (SCHEDULED, TEMP, SUSPEND))


# %% LOOP DATA (BINARY T/F)


# %% BOLUS EVENTS (CORRECTION, AND MEAL INCLUING: CARBS, EXTENDED, DUAL)


# %% CGM DATA


# %% NUMBER OF DAYS OF PUMP AND CGM DATA, OVERALL AND PER EACH AGE & YLW


# %% STATS PER EACH TYPE, OVERALL AND PER EACH AGE & YLW (MIN, PERCENTILES, MAX, MEAN, SD, IQR, COV)


# %% SAVE RESULTS


# %% MAKE THIS A FUNCTION SO THAT IT CAN BE RUN PER EACH INDIVIDUAL
        else:
            metadata["flags"] = "no bolus wizard data"
    else:
        metadata["flags"] = "file contains no data"
else:
    metadata["flags"] = "file does not exist"

# %% V2 DATA TO GRAB
# ALERT SETTINGS
# ESTIMATED LOCAL TIME
# PUMP AND CGM DEVICE ()
# GLYCEMIC OUTCOMES
# DO NOT ROUND DATA
# INFUSION SITE CHANGES
# CGM CALIBRATIONS
