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
import numpy as np
from pytz import timezone
from datetime import timedelta
import datetime as dt
import os
import argparse
import pdb
pd.options.mode.chained_assignment = None  # default='warn'

# %% USER INPUTS (ADD THIS IN LATER)
codeDescription = "Get user's settings and events"
parser = argparse.ArgumentParser(description=codeDescription)

parser.add_argument("-d",
                    "--date-stamp",
                    dest="dateStamp",
                    default="2018-09-28",
                    help="date in '%Y-%m-%d' format of unique donor list" +
                    "(e.g., PHI-2018-03-02-uniqueDonorList)")

parser.add_argument("-s",
                    "--start-index",
                    dest="startIndex",
                    default=0,
                    help="donor index (integer) to start at")

parser.add_argument("-e",
                    "--end-index",
                    dest="endIndex",
                    default=-1,
                    help="donor index (integer) to end at," +
                    "-1 will result in 1 file if startIndex != 0," +
                    "and will default to number of unique donors" +
                    "if startIndex = 0, or endIndex = -2")


args = parser.parse_args()
# %% FUNCTIONS
def defineStartAndEndIndex(args, nDonors):
    startIndex = int(args.startIndex)
    endIndex = int(args.endIndex)
    if endIndex == -1:
        if startIndex == 0:
            endIndex = nDonors
        else:
            endIndex = startIndex + 1
    if endIndex == -2:
        endIndex = nDonors
    return startIndex, endIndex


# CLEAN DATA FUNCTIONS
def removeNegativeDurations(df):
    if "duration" in list(df):
        nNegativeDurations = sum(df.duration < 0)
        if nNegativeDurations > 0:
            df = df[~(df.duration < 0)]
    else:
        nNegativeDurations = np.nan

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


    if "payload.calibration_reading" in list(df):

        searchfor = ['tan']
        tandemDataIndex = ((df.deviceId.str.contains('|'.join(searchfor))) &
                           (df.type == "deviceEvent"))


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
def tempRemoveFields(df, removeFields):


    tempRemoveFields = list(set(df) & set(removeFields))
    tempDf = df[tempRemoveFields]
    df = df.drop(columns=tempRemoveFields)

    return df, tempDf


def flattenJson(df, doNotFlattenList):
    # remove fields that we don't want to flatten
    df, holdData = tempRemoveFields(df, doNotFlattenList)

    # get a list of data types of column headings
    columnHeadings = list(df)

    # loop through each columnHeading
    newDataFrame = pd.DataFrame()

    for colHead in columnHeadings:
        if any(isinstance(item, list) for item in df[colHead]):
            listBlob = df[colHead][df[colHead].astype(str).str[0] == "["]
            df.loc[listBlob.index, colHead] = df.loc[listBlob.index, colHead].str[0]

        # if the df field has embedded json
        if any(isinstance(item, dict) for item in df[colHead]):
            # grab the data that is in brackets
            jsonBlob = df[colHead][df[colHead].astype(str).str[0] == "{"]

            # replace those values with nan
            df.loc[jsonBlob.index, colHead] = np.nan

            # turn jsonBlob to dataframe
            newDataFrame = pd.concat([newDataFrame, pd.DataFrame(jsonBlob.tolist(),
                                     index=jsonBlob.index).add_prefix(colHead + '.')], axis=1)

    df = pd.concat([df, newDataFrame, holdData], axis=1)

    df.sort_index(axis=1, inplace=True)

    return df


def mergeWizardWithBolus(df):

    if "wizard" in df["type"].unique():
        bolusData = df[df.type == "bolus"].copy().dropna(axis=1, how="all")
        wizardData = df[df.type == "wizard"].copy().dropna(axis=1, how="all")

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


def mgdL_to_mmolL(mgdL):
    return mgdL / 18.01559


def round_time(df, timeIntervalMinutes=5, timeField="time",
               roundedTimeFieldName="roundedTime", startWithFirstRecord=True,
               verbose=False):
    '''
    A general purpose round time function that rounds the "time"
    field to nearest <timeIntervalMinutes> minutes
    INPUTS:
        * a dataframe (df) that contains a time field that you want to round
        * timeIntervalMinutes (defaults to 5 minutes given that most cgms output every 5 minutes)
        * timeField to round (defaults to the UTC time "time" field)
        * roundedTimeFieldName is a user specified column name (defaults to roundedTime)
        * startWithFirstRecord starts the rounding with the first record if True, and the last record if False (defaults to True)
        * verbose specifies whether the extra columns used to make calculations are returned
    '''

    df.sort_values(by=timeField, ascending=startWithFirstRecord, inplace=True)
    df.reset_index(drop=True, inplace=True)

    # make sure the time field is in the right form
    t = pd.to_datetime(df[timeField])

    # calculate the time between consecutive records
    t_shift = pd.to_datetime(df[timeField].shift(1))
    df["timeBetweenRecords"] = \
        round((t - t_shift).dt.days*(86400/(60 * timeIntervalMinutes)) +
              (t - t_shift).dt.seconds/(60 * timeIntervalMinutes)) * timeIntervalMinutes

    # separate the data into chunks if timeBetweenRecords is greater than
    # 2 times the <timeIntervalMinutes> minutes so the rounding process starts over
    largeGaps = list(df.query("abs(timeBetweenRecords) > " + str(timeIntervalMinutes * 2)).index)
    largeGaps.insert(0, 0)
    largeGaps.append(len(df))

    for gIndex in range(0, len(largeGaps) - 1):
        chunk = t[largeGaps[gIndex]:largeGaps[gIndex+1]]
        firstRecordChunk = t[largeGaps[gIndex]]

        # calculate the time difference between each time record and the first record
        df.loc[largeGaps[gIndex]:largeGaps[gIndex+1], "minutesFromFirstRecord"] = \
            (chunk - firstRecordChunk).dt.days*(86400/(60)) + (chunk - firstRecordChunk).dt.seconds/(60)

        # then round to the nearest X Minutes
        # NOTE: the ".000001" ensures that mulitples of 2:30 always rounds up.
        df.loc[largeGaps[gIndex]:largeGaps[gIndex+1], "roundedMinutesFromFirstRecord"] = \
            round((df.loc[largeGaps[gIndex]:largeGaps[gIndex+1],
                          "minutesFromFirstRecord"] / timeIntervalMinutes) + 0.000001) * (timeIntervalMinutes)

        roundedFirstRecord = (firstRecordChunk + pd.Timedelta("1microseconds")).round(str(timeIntervalMinutes) + "min")
        df.loc[largeGaps[gIndex]:largeGaps[gIndex+1], roundedTimeFieldName] = \
            roundedFirstRecord + \
            pd.to_timedelta(df.loc[largeGaps[gIndex]:largeGaps[gIndex+1],
                                   "roundedMinutesFromFirstRecord"], unit="m")

    # sort by time and drop fieldsfields
    df.sort_values(by=timeField, ascending=startWithFirstRecord, inplace=True)
    df.reset_index(drop=True, inplace=True)
    if verbose is False:
        df.drop(columns=["timeBetweenRecords",
                         "minutesFromFirstRecord",
                         "roundedMinutesFromFirstRecord"], inplace=True)

    return df


def get_descriptive_stats(df, newName, dataSubType):

    newDf = df[dataSubType].describe().add_suffix(newName)

    newDf[("rangeOf" + newName)] = \
        newDf[("max" + newName)] - \
        newDf[("min" + newName)]

    return newDf


def get_bolusDaySummary(bolusData):

    if "extended" not in bolusData:
        bolusData["extended"] = 0

    bolusByDay = bolusData.groupby(bolusData["day"])

    # total bolus insulin for each day
    bolusDaySummary = pd.DataFrame(bolusByDay.normal.sum())
    bolusDaySummary = bolusDaySummary.rename(columns={"normal":"totalAmountOfNormalBolusInsulin"})

    bolusDaySummary["totalAmountOfExtendedBolusInsulin"] = bolusByDay.extended.sum().fillna(0.0)
    bolusDaySummary["totalAmountOfBolusInsulin"] = bolusDaySummary["totalAmountOfNormalBolusInsulin"].fillna(0.0) + \
                                           bolusDaySummary["totalAmountOfExtendedBolusInsulin"].fillna(0.0)

    # bolus range for normal boluses
    normalBasalDF = get_descriptive_stats(bolusByDay, "NormalBolusAmountPerBolus", "normal")
    bolusDaySummary = pd.concat([bolusDaySummary, normalBasalDF], axis = 1)

    # total number of bolus types per day
    bolusTypePerDay = bolusData.groupby(["day",
                                         "subType"]).size().unstack()

    bolusDaySummary["numberOfNormalBoluses"] = bolusTypePerDay["normal"].fillna(0)

    if "square" not in list(bolusTypePerDay):
        bolusDaySummary["numberOfSquareBoluses"] = 0
    else:
        bolusDaySummary["numberOfSquareBoluses"] = bolusTypePerDay["square"].fillna(0)

    if "dual/square" not in list(bolusTypePerDay):
        bolusDaySummary["numberOfDualBoluses"] = 0
    else:
        bolusDaySummary["numberOfDualBoluses"] = bolusTypePerDay["dual/square"].fillna(0)

    bolusDaySummary["numberOfAllBolusTypes"] = bolusDaySummary["numberOfNormalBoluses"] + \
                                        bolusDaySummary["numberOfSquareBoluses"] + \
                                        bolusDaySummary["numberOfDualBoluses"]

    return bolusDaySummary


def get_basalDaySummary(basal):
    # group data by day
    basalByDay = basal.groupby(basal["day"])

    # total basal insulin per day
    basalDaySummary = pd.DataFrame(basalByDay.totalAmountOfBasalInsulin.sum())

    # total number of basals types per day
    basalTypePerDay = basal.groupby(["day", "deliveryType"]).size().unstack()

    basalDaySummary["numberOfScheduledBasals"] = basalTypePerDay["scheduled"].fillna(0)
    if "suspend" not in list(basalTypePerDay):
        basalDaySummary["numberOfSuspendedBasals"] = 0
    else:
        basalDaySummary["numberOfSuspendedBasals"] = basalTypePerDay["suspend"].fillna(0)
    if "temp" not in list(basalTypePerDay):
        basalDaySummary["numberOfTempBasals"] = 0
    else:
        basalDaySummary["numberOfTempBasals"] = basalTypePerDay["temp"].fillna(0)

    basalDaySummary["totalNumberOfBasals"] = basalDaySummary["numberOfScheduledBasals"] + \
                                 basalDaySummary["numberOfTempBasals"]

    return basalDaySummary


def filterAndSort(groupedDF, filterByField, sortByField):
    filterDF = groupedDF.get_group(filterByField).dropna(axis=1, how="all")
    filterDF = filterDF.sort_values(sortByField)
    return filterDF


def getClosedLoopDays(groupedData, nTempBasalsPerDayIsClosedLoop, metadata):
    # filter by basal data and sort by time
    if "basal" in groupedData.type.unique():
        basalData = filterAndSort(groupedData, "basal", "time")

        # get closed loop days
        nTB = nTempBasalsPerDayIsClosedLoop

        tbDataFrame = basalData.loc[basalData.deliveryType == "temp", ["time"]]
        tbDataFrame.index = pd.to_datetime(tbDataFrame["time"])
        tbDataFrame = tbDataFrame.drop(["time"], axis=1)
        tbDataFrame["basal.temp.count"] = 1
        nTempBasalsPerDay = tbDataFrame.resample("D").sum()
        closedLoopDF = pd.DataFrame(nTempBasalsPerDay,
                                    index=nTempBasalsPerDay.index.date)
        closedLoopDF["day"] = nTempBasalsPerDay.index.date
        closedLoopDF["basal.closedLoopDays"] = \
            closedLoopDF["basal.temp.count"] >= nTB
        nClosedLoopDays = closedLoopDF["basal.closedLoopDays"].sum()

        # get the number of days with 670g
        basalData["day"] = pd.to_datetime(basalData.time).dt.date
        bdGroup = basalData.groupby("day")
        topPump = bdGroup.deviceId.describe()["top"]
        med670g = pd.DataFrame(topPump.str.contains("1780")).rename(columns={"top":"670g"})
        med670g.reset_index(inplace=True)
        n670gDays = med670g["670g"].sum()
        if n670gDays == 0:
            med670g = pd.DataFrame(columns=["670g", "day"])


    else:
        closedLoopDF = pd.DataFrame(columns=["basal.closedLoopDays", "day"])
        med670g = pd.DataFrame(columns=["670g", "day"])
        nClosedLoopDays = 0
        n670gDays = 0

    metadata["basal.closedLoopDays.count"] = nClosedLoopDays
    metadata["med670gDays.count"] = n670gDays

    return closedLoopDF, med670g, metadata


def removeDuplicates(df, criteriaDF):
    nBefore = len(df)
    df = df.loc[~(df[criteriaDF].duplicated())]
    df = df.reset_index(drop=True)
    nDuplicatesRemoved = nBefore - len(df)

    return df, nDuplicatesRemoved


def removeCgmDuplicates(df, timeCriterion):
    if timeCriterion in df:
        df.sort_values(by=[timeCriterion, "uploadTime"],
                       ascending=[False, False],
                       inplace=True)
        dfIsNull = df[df[timeCriterion].isnull()]
        dfNotNull = df[df[timeCriterion].notnull()]
        dfNotNull, nDuplicatesRemoved = removeDuplicates(dfNotNull, [timeCriterion, "value"])
        df = pd.concat([dfIsNull, dfNotNull])
        df.sort_values(by=[timeCriterion, "uploadTime"],
                       ascending=[False, False],
                       inplace=True)
    else:
        nDuplicatesRemoved = 0

    return df, nDuplicatesRemoved


def getStartAndEndTimes(df, dateTimeField):
    dfBeginDate = df[dateTimeField].min()
    dfEndDate = df[dateTimeField].max()

    return dfBeginDate, dfEndDate


def getListOfDexcomCGMDays(df):
    # search for dexcom cgms
    searchfor = ["Dex", "tan", "IR", "unk"]
    # create dexcom boolean field
    if "deviceId" in df.columns.values:
        totalCgms = len(df.deviceId.notnull())
        df["dexcomCGM"] = df.deviceId.str.contains("|".join(searchfor))
        percentDexcomCGM = df.dexcomCGM.sum() / totalCgms * 100
    else:
        percentDexcomCGM = np.nan
    return df, percentDexcomCGM


def load_csv(dataPathAndName):
    df = pd.read_csv(dataPathAndName, low_memory=False)
    return df


def load_json(dataPathAndName):
    df = pd.read_json(dataPathAndName, orient="records")
    return df


def getTzoForDateTime(utcTime, currentTimezone):

    tz = timezone(currentTimezone)
    tzoNum = int(tz.localize(utcTime).strftime("%z"))
    tzoNum = int(tz.localize(utcTime).strftime("%z"))
    tzoHours = np.floor(tzoNum / 100)
    tzoMinutes = round((tzoNum / 100 - tzoHours) * 100, 0)
    tzoSign = np.sign(tzoHours)
    tzo = int((tzoHours * 60) + (tzoMinutes * tzoSign))
    localTime = utcTime + pd.to_timedelta(tzo, unit="m")

    return localTime


def getTimezoneOffset(currentDate, currentTimezone):

    # edge case for 'US/Pacific-New'
    if currentTimezone == 'US/Pacific-New':
        currentTimezone = 'US/Pacific'

    tz = timezone(currentTimezone)
    # here we add 1 day to the current date to account for changes to/from DST
    tzoNum = int(tz.localize(currentDate + timedelta(days=1)).strftime("%z"))
    tzoHours = np.floor(tzoNum / 100)
    tzoMinutes = round((tzoNum / 100 - tzoHours) * 100, 0)
    tzoSign = np.sign(tzoHours)
    tzo = int((tzoHours * 60) + (tzoMinutes * tzoSign))

    return tzo


def isDSTChangeDay(currentDate, currentTimezone):
    if currentTimezone == 'US/Pacific-New':
        currentTimezone = 'US/Pacific'
    tzoCurrentDay = getTimezoneOffset(pd.to_datetime(currentDate),
                                      currentTimezone)
    tzoPreviousDay = getTimezoneOffset(pd.to_datetime(currentDate) +
                                       timedelta(days=-1), currentTimezone)

    return (tzoCurrentDay != tzoPreviousDay)


def get_setting_durations(df, col, dataPulledDF):
    df = pd.concat([df, dataPulledDF], sort=False)
    df.sort_values(col + ".localTime", inplace=True)
    df.reset_index(inplace=True, drop=True)
    df.fillna(method='ffill', inplace=True)
    durationHours = (df[col + ".localTime"].shift(-1) -
                     df[col + ".localTime"]).dt.total_seconds() / 3600
    durationHours.fillna(0, inplace=True)
    durationHours[durationHours > 24] = 24
    df[col + ".durationHours"] = durationHours

    return df


def get_settingStats(df, col, pumpCol):
    df[col] = df[pumpCol]
    df[col + ".min"] = df[col].min()
    df[col + ".weightedMean"] = np.sum(df[col] * df[col + ".durationHours"]) / df[col + ".durationHours"].sum()
    df[col + ".max"] = df[col].max()

    return df


def getPumpSettingsStats(df, col, pumpCol):
    pumpColHeadings = [col + ".localTime", col, col + ".min",
                       col + ".weightedMean", col + ".max"]
    df[col] = df[pumpCol + ".amount"]
    df[col + ".localTime"] = pd.to_datetime(df["day"]) + \
        pd.to_timedelta(df[pumpCol + ".start"], unit="ms")
    df[col + ".min"] = df[col]
    df[col + ".weightedMean"] = df[col]
    df[col + ".max"] = df[col]

    df2 = df.loc[df[pumpCol + ".amount"].notnull(), pumpColHeadings]

    return df, df2


def isf_likely_units(df, columnHeading):
    isfNotNull = df[df[columnHeading].notnull()][columnHeading]
    minVal = np.min(isfNotNull)
    maxVal = np.max(isfNotNull)
    minDiff = np.abs(minVal - np.round(minVal))
    maxDiff = np.abs(maxVal - np.round(maxVal))
    if ((maxDiff == 0) & (maxDiff == 0) & (maxVal > 22.1)):
        likelyUnits = "mg/dL"
    else:
        likelyUnits = "mmol/L"
    return likelyUnits



# %% DELELET LATER
args.startIndex = 96


# %% START OF CODE
dataPulledDate = args.dateStamp
dataPulledDF = pd.DataFrame(pd.to_datetime(dataPulledDate), columns=["day"], index=[0])
dataPulledDF["day"] = dataPulledDF["day"].dt.date
phiDate = "PHI-" + dataPulledDate
donorPath = os.path.join("..", "bigdata-processing-pipeline", "data", phiDate + "-donor-data")

phiOutputPath = os.path.join(donorPath, "PHI-settings-and-events")
outputPath = os.path.join(donorPath, "settings-and-events")

# create anonExportDataPath folders
if not os.path.exists(phiOutputPath):
    os.makedirs(phiOutputPath)
    os.makedirs(outputPath)

donorList = phiDate + "-uniqueDonorList.csv"
donors = load_csv(os.path.join(donorPath, donorList))

allMetadata = pd.DataFrame()
allAgeSummaries = pd.DataFrame()
allYlwSummaries = pd.DataFrame()
allAgeANDylwSummaries = pd.DataFrame()

# %% MAKE THIS A FUNCTION SO THAT IT CAN BE RUN PER EACH INDIVIDUAL
nUniqueDonors = len(donors)

# define start and end index
startIndex, endIndex = defineStartAndEndIndex(args, nUniqueDonors)

for dIndex in range(startIndex, endIndex):
    # % ID, HASHID, AGE, & YLW
    userID = donors.userID[dIndex]
    hashID = donors.hashID[dIndex]
    metadata = pd.DataFrame(index=[dIndex])
    metadata["hashID"] = hashID

    try:
        # make folder to save data
        processedDataPath = os.path.join(phiOutputPath, "PHI-" + userID)
        if not os.path.exists(processedDataPath):
            os.makedirs(processedDataPath)

        # round all birthdays and diagnosis dates to the first day of the month (to protect identities)
        if (pd.isnull(donors.bDay[dIndex]) + pd.isnull(donors.dDay[dIndex])) == 0:

            bDate = pd.to_datetime(donors.bDay[dIndex][0:7])
            dDate = pd.to_datetime(donors.dDay[dIndex][0:7])


            # %% LOAD IN DONOR JSON DATA

            jsonDataPath = os.path.join(donorPath, phiDate + "-donorJsonData")
            jsonFileName = os.path.join(jsonDataPath, "PHI-" + userID + ".json")

            if os.path.exists(jsonFileName):
                fileSize = os.stat(jsonFileName).st_size
                metadata["fileSizeKB"] = fileSize / 1000
                if fileSize > 1000:
                    data = load_json(jsonFileName)

                    # sort the data by time
                    data.sort_values("time", inplace=True)

                    # flatten the embedded json
                    doNotFlattenList = ["suppressed", "recommended", "payload"]
                    data = flattenJson(data, doNotFlattenList)


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
                    if (("upload" in data.type.unique()) &
                        ("basal" in data.type.unique()) &
                        ("bolus" in data.type.unique()) &
                        ("cbg" in data.type.unique()) &
                        ("pumpSettings" in data.type.unique())):
                        data = addUploadDate(data)


                        # %% TIME (UTC, TIMEZONE, DAY AND EVENTUALLY LOCAL TIME)
                        data["utcTime"] = pd.to_datetime(data["time"])
                        data["timezone"].fillna(method='ffill', inplace=True)
                        data["timezone"].fillna(method='bfill', inplace=True)
                        data["day"] = pd.DatetimeIndex(data["utcTime"]).date

                        # round to the nearest 5 minutes
                        # TODO: once roundTime is pushed to tidals repository then this line can be replaced
                        # with td.clean.round_time
                        data = round_time(data, timeIntervalMinutes=5, timeField="time",
                                          roundedTimeFieldName="roundedTime", startWithFirstRecord=True,
                                          verbose=False)
                        data.sort_values("uploadTime", ascending=False, inplace=True)


                        # %% ID, HASHID, AGE, & YLW
                        data["userID"] = userID
                        data["hashID"] = hashID
                        data["age"] = np.floor((data["utcTime"] - bDate).dt.days/365.25).astype(int)
                        data["ylw"] = np.floor((data["utcTime"] - dDate).dt.days/365.25).astype(int)


                        # %% BOLUS EVENTS (CORRECTION, AND MEAL INCLUING: CARBS, EXTENDED, DUAL)
                        bolus = mergeWizardWithBolus(data)
                        if len(bolus) > 0:
                            # get rid of duplicates that have the same ["time", "normal"]
                            bolus.sort_values("uploadTime", ascending=False, inplace=True)
                            bolus, nBolusDuplicatesRemoved = \
                                removeDuplicates(bolus, ["deviceTime", "normal"])
                            metadata["nBolusDuplicatesRemoved"] = nBolusDuplicatesRemoved

                            # get a summary of boluses per day
                            bolusDaySummary = get_bolusDaySummary(bolus)

                            # figure out likely isf units
                            isfUnits = isf_likely_units(bolus, "insulinSensitivity")
                            metadata["bolus.isfLikelyUnits"] = isfUnits

                            if isfUnits in "mmol/L":

                                bolus["isf_mmolL_U"] = bolus["insulinSensitivity"]
                                bolus["isf"] = mmolL_to_mgdL(bolus["isf_mmolL_U"])

                            else:
                                # I am pretty sure this case does NOT exist
                                pdb.set_trace()
                                bolus["isf"] = bolus["insulinSensitivity"]
                                bolus["isf_mmolL_U"]  = mgdL_to_mmolL(bolus["isf"])


                            bolusCH = ["utcTime", "timezone", "roundedTime", "normal", "carbInput", "subType",
                                            "insulinOnBoard", "bgInput",
                                            "isf", "isf_mmolL_U", "insulinCarbRatio"]
                            bolusEvents = bolus.loc[bolus["normal"].notnull(), bolusCH]
                            bolusEvents.loc[bolusEvents["bgInput"] == 0, "bgInput"] = np.nan
                            bolusEvents = bolusEvents.rename(columns={"normal": "unitsInsulin",
                                                                      "bgInput": "bg_mmolL"})
                            bolusEvents["bg_mgdL"] = mmolL_to_mgdL(bolusEvents["bg_mmolL"])
                            bolusEvents["eventType"] = "correction"
                            bolusEvents.loc[bolusEvents["carbInput"] > 0, "eventType"] = "meal"

                            if "duration" in list(bolus):
                                bolus["duration"].replace(0, np.nan, inplace=True)
                                bolus["durationHours"] = bolus["duration"] / 1000.0 / 3600.0
                                bolus["rate"] = bolus["extended"] / bolus["durationHours"]
    #                            bolusExtendedCH = commonColumnHeadings.copy()
                                bolusExtendedCH = ["utcTime", "timezone", "roundedTime", "durationHours", "rate",  "type"]
                                bolusExtendedEvents = bolus.loc[
                                        ((bolus["extended"].notnull()) &
                                         (bolus["duration"] > 0)), bolusExtendedCH]

                            if "extended" not in bolus:
                                bolus["extended"] = np.nan
                                bolus["duration"] = np.nan


                            # get start and end times
                            bolusBeginDate, bolusEndDate = getStartAndEndTimes(bolus, "day")
                            metadata["bolus.beginDate"] = bolusBeginDate
                            metadata["bolus.endDate"] = bolusEndDate


                            # %% PUMP SETTINGS

                            pumpSettings = data[data.type == "pumpSettings"].copy().dropna(axis=1, how="all")
                            pumpSettings.sort_values("uploadTime", ascending=False, inplace=True)

                            pumpSettings, nPumpSettingsDuplicatesRemoved = \
                            removeDuplicates(pumpSettings, "deviceTime")
                            metadata["nPumpSettingsDuplicatesRemoved"] = nPumpSettingsDuplicatesRemoved

                            pumpSettings.sort_values("utcTime", ascending=True, inplace=True)
                            pumpSettings.reset_index(drop=True, inplace=True)

                            # ISF
                            isfColHeadings = ["isf.localTime", "isf", "isf_mmolL_U"]

                            if "insulinSensitivity.amount" in list(pumpSettings):
                                isfColHead = "insulinSensitivity"

                                # figure out likely isf units
                                isfUnits = isf_likely_units(pumpSettings, "insulinSensitivity.amount")
                                metadata["pumpSettings.isfLikelyUnits"] = isfUnits

                                if isfUnits in "mmol/L":

                                    pumpSettings["isf_mmolL_U"] = pumpSettings[isfColHead + ".amount"]
                                    pumpSettings["isf"] = mmolL_to_mgdL(pumpSettings["isf_mmolL_U"])

                                else:

                                    pumpSettings["isf"] = pumpSettings[isfColHead + ".amount"]
                                    pumpSettings["isf_mmolL_U"] = mgdL_to_mmolL(pumpSettings["isf"])

                                pumpSettings["isf.localTime"] = pd.to_datetime(pumpSettings["day"]) + \
                                    pd.to_timedelta(pumpSettings[isfColHead + ".start"], unit="ms")

                                isf = pumpSettings.loc[pumpSettings["isf"].notnull(), isfColHeadings]

                                # add a day summary
                                isfDaySummary = pd.DataFrame()
                                isfDaySummary["day"] = isf["isf.localTime"].dt.date
                                isfDaySummary["isf.min"] = isf["isf"]
                                isfDaySummary["isf.weightedMean"] = isf["isf"]
                                isfDaySummary["isf.max"] = isf["isf"]

                            else:
                                isfColHead = "insulinSensitivities"
                                isf = pd.DataFrame(columns=isfColHeadings)
                                isfDayColHeadings = ['day', 'isf.min', 'isf.weightedMean', 'isf.max']
                                isfDaySummary = pd.DataFrame(columns=isfDayColHeadings)
                                for p, actSched in zip(pumpSettings.index, pumpSettings["activeSchedule"]):
                                    # edge case where actSchedule is float
                                    if isinstance(actSched, float):
                                        actSched = str(int(actSched))

                                    tempDF = pd.DataFrame(pumpSettings.loc[p, isfColHead + "." + actSched])
                                    tempDF["day"] = pumpSettings.loc[p, "day"]
                                    tempDF["isf.localTime"] = pd.to_datetime(tempDF["day"]) + pd.to_timedelta(tempDF["start"], unit="ms")

                                    # figure out likely isf units
                                    isfUnits = isf_likely_units(tempDF, "amount")
                                    metadata["tempDF.isfLikelyUnits"] = isfUnits

                                    if isfUnits in "mmol/L":

                                        tempDF["isf_mmolL_U"] = tempDF["amount"]
                                        tempDF["isf"] = mmolL_to_mgdL(tempDF["isf_mmolL_U"])

                                    else:

                                        tempDF["isf"] = tempDF["amount"]
                                        tempDF["isf_mmolL_U"] = mgdL_to_mmolL(tempDF["isf"])

                                    endOfDay = pd.DataFrame(pd.to_datetime(pumpSettings.loc[p, "day"] + pd.Timedelta(1, "D")), columns=["isf.localTime"], index=[0])
                                    tempDF = get_setting_durations(tempDF, "isf", endOfDay)
                                    tempDF = tempDF[:-1]

                                    tempDaySummary = pd.DataFrame(index=[0])
                                    tempDaySummary["day"] = tempDF["isf.localTime"].dt.date
                                    tempDaySummary["isf.min"] = tempDF["isf"].min()
                                    tempDaySummary["isf.weightedMean"] = \
                                        np.sum(tempDF["isf"] * tempDF["isf.durationHours"]) / tempDF["isf.durationHours"].sum()
                                    tempDaySummary["isf.max"] = tempDF["isf"].max()

                                    isf = pd.concat([isf, tempDF[isfColHeadings]], ignore_index=True)
                                    isfDaySummary = pd.concat([isfDaySummary, tempDaySummary], ignore_index=True)

                            isfDaySummary = pd.concat([isfDaySummary, dataPulledDF], sort=False)
                            isfDaySummary.reset_index(inplace=True, drop=True)
                            isfDaySummary.fillna(method='ffill', inplace=True)
                            # it is possible for someone to someone to change their schedule
                            # in the middle of the day, take the latest change as the schedule
                            # for that day.
                            isfDaySummary.drop_duplicates(subset="day", keep="last", inplace=True)
                            isfDaySummary.reset_index(inplace=True, drop=True)

                            # CIR
                            cirColHeadings = ["cir.localTime", "cir"]

                            if "carbRatio.amount" in list(pumpSettings):
                                cirColHead = "carbRatio"
                                pumpSettings["cir"] = pumpSettings[cirColHead + ".amount"]
                                pumpSettings["cir.localTime"] = pd.to_datetime(pumpSettings["day"]) + \
                                    pd.to_timedelta(pumpSettings[cirColHead + ".start"], unit="ms")

                                cir = pumpSettings.loc[pumpSettings["carbRatio.amount"].notnull(), cirColHeadings]

                                # add a day summary
                                cirDaySummary = pd.DataFrame()
                                cirDaySummary["day"] = cir["cir.localTime"].dt.date
                                cirDaySummary["cir.min"] = cir["cir"]
                                cirDaySummary["cir.weightedMean"] = cir["cir"]
                                cirDaySummary["cir.max"] = cir["cir"]

                            else:

                                cirColHead = "carbRatios"
                                cir = pd.DataFrame(columns=cirColHeadings)
                                cirDayColHeadings = ['day', 'cir.min', 'cir.weightedMean', 'cir.max']
                                cirDaySummary = pd.DataFrame(columns=cirDayColHeadings)
                                for p, actSched in zip(pumpSettings.index, pumpSettings["activeSchedule"]):
                                    # edge case where actSchedule is float
                                    if isinstance(actSched, float):
                                        actSched = str(int(actSched))

                                    tempDF = pd.DataFrame(pumpSettings.loc[p, cirColHead + "." + actSched])
                                    tempDF["day"] = pumpSettings.loc[p, "day"]
                                    tempDF["cir.localTime"] = pd.to_datetime(tempDF["day"]) + pd.to_timedelta(tempDF["start"], unit="ms")
                                    tempDF["cir"] = tempDF["amount"]
                                    endOfDay = pd.DataFrame(pd.to_datetime(pumpSettings.loc[p, "day"] + pd.Timedelta(1, "D")), columns=["cir.localTime"], index=[0])
                                    tempDF = get_setting_durations(tempDF, "cir", endOfDay)
                                    tempDF = tempDF[:-1]

                                    tempDaySummary = pd.DataFrame(index=[0])
                                    tempDaySummary["day"] = tempDF["cir.localTime"].dt.date
                                    tempDaySummary["cir.min"] = tempDF["cir"].min()
                                    tempDaySummary["cir.weightedMean"] = \
                                        np.sum(tempDF["cir"] * tempDF["cir.durationHours"]) / tempDF["cir.durationHours"].sum()
                                    tempDaySummary["cir.max"] = tempDF["cir"].max()

                                    cir = pd.concat([cir, tempDF[cirColHeadings]], ignore_index=True)
                                    cirDaySummary = pd.concat([cirDaySummary, tempDaySummary], ignore_index=True)

                            cirDaySummary = pd.concat([cirDaySummary, dataPulledDF], sort=False)
                            cirDaySummary.fillna(method='ffill', inplace=True)
                            # it is possible for someone to someone to change their schedule
                            # in the middle of the day, take the latest change as the schedule
                            # for that day.
                            cirDaySummary.drop_duplicates(subset="day", keep="last", inplace=True)
                            cirDaySummary.reset_index(inplace=True, drop=True)


                            # CORRECTION TARGET
                            ctColHeadings = ['deviceId', "ct.localTime", "ct.low", "ct.high", "ct.target", "ct.range"]
                            ctDayColHeadings = ['day', 'deviceId', "ct.low", "ct.high", "ct.target", "ct.range",
                                                "ct.target.min", "ct.target.weightedMean", "ct.target.max"]

                            if "bgTarget.start" in list(pumpSettings):
                                ctColHead = "bgTarget."

                                for targetType in ["low", "high", "target", "range"]:
                                    if ctColHead + targetType in list(pumpSettings):
                                        pumpSettings["ct." + targetType + "_mmolL"] = \
                                            pumpSettings[ctColHead + targetType]

                                        pumpSettings["ct." + targetType] = \
                                            mmolL_to_mgdL(pumpSettings["ct." + targetType + "_mmolL"])
                                    else:
                                        pumpSettings["ct." + targetType + "_mmolL"] = np.nan
                                        pumpSettings["ct." + targetType]  = np.nan

                                pumpSettings["ct.localTime"] = pd.to_datetime(pumpSettings["day"]) + \
                                    pd.to_timedelta(pumpSettings[ctColHead + "start"], unit="ms")

                                correctionTarget = pumpSettings.loc[pumpSettings["bgTarget.start"].notnull(), ctColHeadings]

                                # add a day summary
                                ctDaySummary = pd.DataFrame(columns=ctDayColHeadings)
                                ctDaySummary["day"] = correctionTarget["ct.localTime"].dt.date
                                ctDaySummary["deviceId"] = correctionTarget["deviceId"]

                                # medtronic pumps use the target high as the correction target
                                if sum(correctionTarget.deviceId.str.contains("ed")) > 0:
                                    correctionTarget.loc[correctionTarget.deviceId.str.contains("ed"), "ct.target"] = \
                                        correctionTarget.loc[correctionTarget.deviceId.str.contains("ed"), 'ct.high']

                                if sum(correctionTarget.deviceId.str.contains("MMT")) > 0:
                                    correctionTarget.loc[correctionTarget.deviceId.str.contains("MMT"), "ct.target"] = \
                                        correctionTarget.loc[correctionTarget.deviceId.str.contains("MMT"), 'ct.high']

                                for targetType in ["ct.low", "ct.high", "ct.target", "ct.range"]:
                                    ctDaySummary[targetType] = correctionTarget[targetType]

                                ctDaySummary["ct.target.min"] = correctionTarget["ct.target"]
                                ctDaySummary["ct.target.weightedMean"] = correctionTarget["ct.target"]
                                ctDaySummary["ct.target.max"] = correctionTarget["ct.target"]


                            else:

                                ctColHead = "bgTargets"
                                correctionTarget = pd.DataFrame(columns=ctColHeadings)

                                ctDaySummary = pd.DataFrame(columns=ctDayColHeadings)
                                for p, actSched in zip(pumpSettings.index, pumpSettings["activeSchedule"]):
                                    # edge case where actSchedule is float
                                    if isinstance(actSched, float):
                                        actSched = str(int(actSched))

                                    tempDF = pd.DataFrame(pumpSettings.loc[p, ctColHead + "." + actSched])
                                    targetTypes = list(set(list(tempDF)) - set(["start"]))
                                    tempDF["day"] = pumpSettings.loc[p, "day"]
                                    tempDF["deviceId"] = pumpSettings.loc[p, "deviceId"]

                                    for targetType in ["low", "high", "target", "range"]:
                                        if targetType in list(tempDF):
                                            tempDF["ct." + targetType + "_mmolL"] = \
                                                tempDF[targetType]

                                            tempDF["ct." + targetType] = \
                                                mmolL_to_mgdL(tempDF["ct." + targetType + "_mmolL"])
                                        else:
                                            tempDF["ct." + targetType + "_mmolL"] = np.nan
                                            tempDF["ct." + targetType]  = np.nan

                                    tempDF["ct.localTime"] = pd.to_datetime(tempDF["day"]) + pd.to_timedelta(tempDF["start"], unit="ms")
                                    endOfDay = pd.DataFrame(pd.to_datetime(pumpSettings.loc[p, "day"] + pd.Timedelta(1, "D")), columns=["ct.localTime"], index=[0])
                                    tempDF = get_setting_durations(tempDF, "ct", endOfDay)
                                    tempDF = tempDF[:-1]

                                    # medtronic pumps use the target high as the correction target
                                    if sum(tempDF.deviceId.str.contains("ed")) > 0:
                                        tempDF.loc[tempDF.deviceId.str.contains("ed"), "ct.target"] = \
                                            tempDF.loc[tempDF.deviceId.str.contains("ed"), 'ct.high']

                                    if sum(tempDF.deviceId.str.contains("MMT")) > 0:
                                        tempDF.loc[tempDF.deviceId.str.contains("MMT"), "ct.target"] = \
                                            tempDF.loc[tempDF.deviceId.str.contains("MMT"), 'ct.high']

                                    tempDaySummary = pd.DataFrame(index=[0], columns=ctDayColHeadings)
                                    tempDaySummary["day"] = tempDF["ct.localTime"].dt.date
                                    tempDaySummary["deviceId"] = tempDF["deviceId"]
                                    tempDaySummary["ct.target.min"] = tempDF["ct.target"].min()
                                    tempDaySummary["ct.target.weightedMean"] = \
                                        np.sum(tempDF["ct.target"] * tempDF["ct.durationHours"]) / tempDF["ct.durationHours"].sum()
                                    tempDaySummary["ct.target.max"] = tempDF["ct.target"].max()

                                    for targetType in ["ct.low", "ct.high", "ct.target", "ct.range"]:
                                        tempDaySummary[targetType] = tempDF[targetType]


                                    correctionTarget = pd.concat([correctionTarget, tempDF[ctColHeadings]], ignore_index=True)
                                    ctDaySummary = pd.concat([ctDaySummary, tempDaySummary[ctDayColHeadings]], ignore_index=True)

                            ctDaySummary = pd.concat([ctDaySummary, dataPulledDF], sort=False)
                            ctDaySummary.fillna(method='ffill', inplace=True)
                            # it is possible for someone to someone to change their schedule
                            # in the middle of the day, take the latest change as the schedule
                            # for that day.
                            ctDaySummary.drop_duplicates(subset="day", keep="last", inplace=True)
                            ctDaySummary.reset_index(inplace=True, drop=True)


                            # SCHEDULED BASAL RATES
                            sbrColHeadings = ["sbr.localTime", "rate", "sbr.type"]
                            sbr = pd.DataFrame(columns=sbrColHeadings)
                            sbrDayColHeadings = ['day', 'sbr.min', 'sbr.weightedMean', 'sbr.max', 'sbr.type']
                            sbrDaySummary = pd.DataFrame(columns=sbrDayColHeadings)
                            for p, actSched in zip(pumpSettings.index, pumpSettings["activeSchedule"]):
                                # edge case where actSchedule is float
                                if isinstance(actSched, float):
                                    actSched = str(int(actSched))
                                if 'Auto Mode' not in actSched:
                                    tempDF = pd.DataFrame(pumpSettings.loc[p, "basalSchedules." + actSched])
                                    tempDF["day"] = pumpSettings.loc[p, "day"]
                                    tempDF["sbr.type"] = "regular"
                                    tempDF["sbr.localTime"] = pd.to_datetime(tempDF["day"]) + pd.to_timedelta(tempDF["start"], unit="ms")
                                    endOfDay = pd.DataFrame(pd.to_datetime(pumpSettings.loc[p, "day"] + pd.Timedelta(1, "D")), columns=["sbr.localTime"], index=[0])
                                    tempDF = get_setting_durations(tempDF, "sbr", endOfDay)
                                    tempDF = tempDF[:-1]

                                    tempDaySummary = pd.DataFrame(index=[0])
                                    tempDaySummary["day"] = tempDF["sbr.localTime"].dt.date
                                    tempDaySummary["sbr.min"] = tempDF["rate"].min()
                                    tempDaySummary["sbr.weightedMean"] = \
                                        np.sum(tempDF["rate"] * tempDF["sbr.durationHours"]) / tempDF["sbr.durationHours"].sum()
                                    tempDaySummary["sbr.max"] = tempDF["rate"].max()
                                    tempDaySummary["sbr.type"] = "regular"

                                else:
                                    tempDF = pd.DataFrame(index=[0])
                                    tempDF["day"] = pumpSettings.loc[p, "day"]
                                    tempDF["sbr.localTime"] = pd.to_datetime(tempDF["day"])
                                    tempDF["rate"] = np.nan
                                    tempDF["sbr.type"] = "AutoMode"

                                    tempDaySummary = pd.DataFrame(index=[0])
                                    tempDaySummary["day"] = tempDF["sbr.localTime"].dt.date
                                    tempDaySummary["sbr.min"] = np.nan
                                    tempDaySummary["sbr.weightedMean"] = np.nan
                                    tempDaySummary["sbr.max"] = np.nan
                                    tempDaySummary["sbr.type"] = "AutoMode"

                                sbr = pd.concat([sbr, tempDF[sbrColHeadings]], ignore_index=True)
                                sbrDaySummary = pd.concat([sbrDaySummary, tempDaySummary], ignore_index=True)

                            sbrDaySummary = pd.concat([sbrDaySummary, dataPulledDF], sort=False)
                            sbrDaySummary.fillna(method='ffill', inplace=True)
                            # it is possible for someone to someone to change their schedule
                            # in the middle of the day, take the latest change as the schedule
                            # for that day.
                            sbrDaySummary.drop_duplicates(subset="day", keep="last", inplace=True)
                            sbrDaySummary.reset_index(inplace=True, drop=True)


                            # %% test this later
    #                        # max basal rate, max bolus amount, and insulin duration
    #                        if "rateMaximum" in list(data):
    #                            pdb.set_trace()
    #                        if "amountMaximum" in list(data):
    #                            pdb.set_trace()
    #                        if "bolus.calculator" in list(data):
    #                            pdb.set_trace()


                            # %% ACTUAL BASAL RATES (TIME, VALUE, DURATION, TYPE (SCHEDULED, TEMP, SUSPEND))
                            basal = data[data.type == "basal"].copy().dropna(axis=1, how="all")
                            basal.sort_values("uploadTime", ascending=False, inplace=True)

                            basalBeginDate, basalEndDate = getStartAndEndTimes(basal, "day")
                            metadata["basal.beginDate"] = basalBeginDate
                            metadata["basal.endDate"] = basalEndDate

                            basal, nBasalDuplicatesRemoved = \
                                removeDuplicates(basal, ["deliveryType", "deviceTime", "duration", "rate"])
                            metadata["basal.nBasalDuplicatesRemoved"] = nBasalDuplicatesRemoved

                            # fill NaNs with 0, as it indicates a suspend (temp basal of 0)
                            basal.rate.fillna(0, inplace=True)

                            # get rid of basals that have durations of 0
                            nBasalDuration0 = sum(basal.duration > 0)
                            basal = basal[basal.duration > 0]
                            metadata["basal.nBasalDuration0"] = nBasalDuration0

                            # get rid of basal durations that are unrealistic
                            nUnrealisticBasalDuration = ((basal.duration < 0) | (basal.duration > 86400000))
                            metadata["nUnrealisticBasalDuration"] = sum(nUnrealisticBasalDuration)
                            basal.loc[nUnrealisticBasalDuration, "duration"] = np.nan

                            # calculate the total amount of insulin delivered (duration * rate)
                            basal["durationHours"] = basal["duration"] / 1000.0 / 3600.0
                            basal["totalAmountOfBasalInsulin"] = basal["durationHours"] * basal["rate"]

                            # actual basal delivered
                            abrColHeadings = ["utcTime", "timezone", "roundedTime", "durationHours", "rate", "type"]
                            abr = basal[abrColHeadings]
                            if "duration" in list(bolus):
                                abr = pd.concat([abr, bolusExtendedEvents], ignore_index=True)
                                abr.sort_values("utcTime", inplace=True)

                            abr["timezone"].fillna(method='ffill', inplace=True)
                            abr["timezone"].fillna(method='bfill', inplace=True)

                            # get a summary of basals per day
                            basalDaySummary = get_basalDaySummary(basal)


                            # %% GET CLOSED LOOP DAYS WITH TEMP BASAL DATA
                            # group data by type
                            groupedData = data.groupby(by="type")

                            isClosedLoopDay, is670g, metadata = \
                                getClosedLoopDays(groupedData, 30, metadata)

                            # %% CGM DATA
                            # filter by cgm and sort by uploadTime
                            cgmData = groupedData.get_group("cbg").dropna(axis=1, how="all")

                            # get rid of duplicates that have the same ["deviceTime", "value"]
                            cgmData, nCgmDuplicatesRemovedDeviceTime = removeCgmDuplicates(cgmData, "deviceTime")
                            metadata["nCgmDuplicatesRemovedDeviceTime"] = nCgmDuplicatesRemovedDeviceTime

                            # get rid of duplicates that have the same ["time", "value"]
                            cgmData, nCgmDuplicatesRemovedUtcTime = removeCgmDuplicates(cgmData, "time")
                            metadata["cnCgmDuplicatesRemovedUtcTime"] = nCgmDuplicatesRemovedUtcTime

                            # get rid of duplicates that have the same "roundedTime"
                            cgmData, nCgmDuplicatesRemovedRoundedTime = removeDuplicates(cgmData, "roundedTime")
                            metadata["nCgmDuplicatesRemovedRoundedTime"] = nCgmDuplicatesRemovedRoundedTime

                            # get start and end times
                            cgmBeginDate, cgmEndDate = getStartAndEndTimes(cgmData, "day")
                            metadata["cgm.beginDate"] = cgmBeginDate
                            metadata["cgm.endDate"] = cgmEndDate

                            # get a list of dexcom cgms
                            cgmData, percentDexcom = getListOfDexcomCGMDays(cgmData)
                            metadata["cgm.percentDexcomCGM"] = percentDexcom

                            # group by date (day) and get stats
                            catDF = cgmData.groupby(cgmData["day"])
                            cgmRecordsPerDay = \
                                pd.DataFrame(catDF.value.count()). \
                                rename(columns={"value": "cgm.count"})
                            dayDate = catDF.day.describe()["top"]
                            dexcomCGM = catDF.dexcomCGM.describe()["top"]
                            nTypesCGM = catDF.dexcomCGM.describe()["unique"]
                            cgmRecordsPerDay["cgm.dexcomOnly"] = \
                                (dexcomCGM & (nTypesCGM == 1))
                            cgmRecordsPerDay["date"] = cgmRecordsPerDay.index

                            # filter the cgm data
                            cgmColHeadings = ["utcTime", "timezone", "roundedTime", "value"]

                            # get data in mg/dL units
                            cgm = cgmData[cgmColHeadings]
                            cgm = cgm.rename(columns={'value': 'mmol_L'})
                            cgm["mg_dL"] = mmolL_to_mgdL(cgm["mmol_L"]).astype(int)


                            # %% NUMBER OF DAYS OF PUMP AND CGM DATA, OVERALL AND PER EACH AGE & YLW

                            # COMBINE DAY SUMMARIES
                            # group by date (day) and get stats
                            catDF = data.groupby(data["day"])
                            dataPerDay = \
                                pd.DataFrame(catDF.hashID.describe()["top"]). \
                                rename(columns={"top": "hashID"})
                            dataPerDay["age"] = catDF.age.mean()
                            dataPerDay["ylw"] = catDF.ylw.mean()
                            dataPerDay["timezone"] = catDF.timezone.describe()["top"]

                            # calculate all of the data start and end range
                            # this can be used for looking at settings
                            dayBeginDate = min(cgmBeginDate, bolusBeginDate, basalBeginDate)
                            dayEndDate = max(cgmEndDate, bolusEndDate, basalEndDate)
                            metadata["day.beginDate"] = dayBeginDate
                            metadata["day.endDate"] = dayEndDate
                            rng = pd.date_range(dayBeginDate, dayEndDate).date
                            dayData = pd.DataFrame(rng, columns=["day"])
                            for dfType in [dataPerDay, basalDaySummary, bolusDaySummary, cgmRecordsPerDay]:
                                dayData = pd.merge(dayData, dfType.reset_index(), on="day", how="left")
                            for dfType in [isClosedLoopDay, is670g]:
                                dayData = pd.merge(dayData, dfType, on="day", how="left")

                            dayData["validPumpData"] = dayData["numberOfNormalBoluses"] > 3
                            dayData["validCGMData"] = dayData["cgm.count"] > (288*.75)

                            dayData["timezone"].fillna(method='ffill', inplace=True)
                            dayData["timezone"].fillna(method='bfill', inplace=True)

                            dayData["isDSTChangeDay"] = dayData[['day', 'timezone']].apply(lambda x: isDSTChangeDay(*x), axis=1)
                            dayData["date"] = pd.to_datetime(dayData["day"])
                            dayData["tzo"] = dayData[['date', 'timezone']].apply(lambda x: getTimezoneOffset(*x), axis=1)

                            # add settings to the dayData
                            dayData = pd.merge(dayData, isfDaySummary, on="day", how="left")
                            dayData = pd.merge(dayData, cirDaySummary, on="day", how="left")
                            dayData = pd.merge(dayData, ctDaySummary, on="day", how="left")
                            dayData = pd.merge(dayData, sbrDaySummary, on="day", how="left")

                            # fill data forward
                            fillList = ['isf.min',
                                        'isf.weightedMean',
                                        'isf.max',
                                        'cir.min',
                                        'cir.weightedMean',
                                        'cir.max',
                                        'ct.low',
                                        'ct.high',
                                        'ct.target',
                                        'ct.range',
                                        'ct.target.min',
                                        'ct.target.weightedMean',
                                        'ct.target.max',
                                        'sbr.min',
                                        'sbr.weightedMean',
                                        'sbr.max',
                                        'sbr.type']
                            for fl in fillList:
                                dayData[fl].fillna(method='ffill', inplace=True)

                            # calculate the start and end of contiguous data
                            # these dates can be used when simulating and predicting, where
                            # you need both pump and cgm data
                            contiguousBeginDate = max(cgmBeginDate, bolusBeginDate, basalBeginDate)
                            contiguousEndDate = min(cgmEndDate, bolusEndDate, basalEndDate)
                            metadata["contiguous.beginDate"] = contiguousBeginDate
                            metadata["contiguous.endDate"] = contiguousEndDate

                            # get a summary by age, and ylw
                            catDF = dayData.groupby("age")
                            ageSummary = pd.DataFrame(catDF.validPumpData.sum())
                            ageSummary.rename(columns={"validPumpData": "nDaysValidPump"}, inplace=True)
                            ageSummary["nDaysValidCgm"] = pd.DataFrame(catDF.validCGMData.sum())
                            ageSummary["nDaysClosedLoop"] = pd.DataFrame(catDF["basal.closedLoopDays"].sum())
                            ageSummary["n670gDays"] = pd.DataFrame(catDF["670g"].sum())

                            # add in isf stats
                            ageSummary["isf.nDays"] = catDF["isf.min"].count()
                            ageSummary["isf.min"] = catDF["isf.min"].min()
                            ageSummary["isf.weightedMean"] = catDF["isf.weightedMean"].sum() / catDF["isf.weightedMean"].count()
                            ageSummary["isf.max"] = catDF["isf.max"].max()

                            # add cir stats
                            ageSummary["cir.nDays"] = catDF["cir.min"].count()
                            ageSummary["cir.min"] = catDF["cir.min"].min()
                            ageSummary["cir.weightedMean"] = catDF["cir.weightedMean"].sum() / catDF["cir.weightedMean"].count()
                            ageSummary["cir.max"] = catDF["cir.max"].max()

                            # add sbr stats
                            ageSummary["sbr.nDays"] = catDF["sbr.min"].count()
                            ageSummary["sbr.min"] = catDF["sbr.min"].min()
                            ageSummary["sbr.weightedMean"] = catDF["sbr.weightedMean"].sum() / catDF["sbr.weightedMean"].count()
                            ageSummary["sbr.max"] = catDF["sbr.max"].max()
                            ageSummary["sbr.nAutoMode"] = catDF["sbr.type"].count()

                            # correctionTarget stats
                            ageSummary["ct.nDays"] = catDF["ct.target.min"].count()
                            ageSummary["ct.target.min"] = catDF["ct.target.min"].min()
                            ageSummary["ct.target.weightedMean"] = catDF["ct.target.weightedMean"].sum() / catDF["ct.target.weightedMean"].count()
                            ageSummary["ct.target.max"] = catDF["ct.target.max"].max()

                            ageSummary.reset_index(inplace=True)

                            analysisCriterion = ageSummary[((ageSummary["nDaysValidPump"]> 28) &
                                                            (ageSummary["nDaysValidCgm"]> 28))]
                            minAge = analysisCriterion["age"].min()
                            maxAge = analysisCriterion["age"].max()
                            nDaysClosedLoop = analysisCriterion["nDaysClosedLoop"].sum()
                            n670gDays = analysisCriterion["n670gDays"].sum()
                            metadata["minAge"] = minAge
                            metadata["maxAge"] = maxAge
                            metadata["nDaysClosedLoop"] = nDaysClosedLoop
                            metadata["n670gDays"] = n670gDays

                            catDF = dayData.groupby("ylw")
                            ylwSummary = pd.DataFrame(catDF.validPumpData.sum())
                            ylwSummary.rename(columns={"validPumpData": "nDaysValidPump"}, inplace=True)
                            ylwSummary["nDaysValidCgm"] = pd.DataFrame(catDF.validCGMData.sum())
                            ylwSummary["nDaysClosedLoop"] = pd.DataFrame(catDF["basal.closedLoopDays"].sum())
                            ylwSummary["n670gDays"] = pd.DataFrame(catDF["670g"].sum())

                            ylwSummary["isf.nDays"] = catDF["isf.min"].count()
                            ylwSummary["isf.min"] = catDF["isf.min"].min()
                            ylwSummary["isf.weightedMean"] = catDF["isf.weightedMean"].sum() / catDF["isf.weightedMean"].count()
                            ylwSummary["isf.max"] = catDF["isf.max"].max()

                            # add cir stats
                            ylwSummary["cir.nDays"] = catDF["cir.min"].count()
                            ylwSummary["cir.min"] = catDF["cir.min"].min()
                            ylwSummary["cir.weightedMean"] = catDF["cir.weightedMean"].sum() / catDF["cir.weightedMean"].count()
                            ylwSummary["cir.max"] = catDF["cir.max"].max()

                            # add sbr stats
                            ylwSummary["sbr.nDays"] = catDF["sbr.min"].count()
                            ylwSummary["sbr.min"] = catDF["sbr.min"].min()
                            ylwSummary["sbr.weightedMean"] = catDF["sbr.weightedMean"].sum() / catDF["sbr.weightedMean"].count()
                            ylwSummary["sbr.max"] = catDF["sbr.max"].max()
                            ylwSummary["sbr.nAutoMode"] = catDF["sbr.type"].count()

                            # correctionTarget stats
                            ylwSummary["ct.nDays"] = catDF["ct.target.min"].count()
                            ylwSummary["ct.target.min"] = catDF["ct.target.min"].min()
                            ylwSummary["ct.target.weightedMean"] = catDF["ct.target.weightedMean"].sum() / catDF["ct.target.weightedMean"].count()
                            ylwSummary["ct.target.max"] = catDF["ct.target.max"].max()

                            ylwSummary.reset_index(inplace=True)

                            analysisCriterion = ylwSummary[((ylwSummary["nDaysValidPump"]> 28) &
                                                            (ylwSummary["nDaysValidCgm"]> 28))]
                            minYLW = analysisCriterion["ylw"].min()
                            maxYLW = analysisCriterion["ylw"].max()
                            metadata["minYLW"] = minYLW
                            metadata["maxYLW"] = maxYLW

                            # age and ylw
                            catDF = dayData.groupby(["age", "ylw"])
                            ageANDylwSummary = pd.DataFrame(catDF.validPumpData.sum())
                            ageANDylwSummary.rename(columns={"validPumpData": "nDaysValidPump"}, inplace=True)
                            ageANDylwSummary["nDaysValidCgm"] = pd.DataFrame(catDF.validCGMData.sum())
                            ageANDylwSummary["nDaysClosedLoop"] = pd.DataFrame(catDF["basal.closedLoopDays"].sum())
                            ageANDylwSummary["n670gDays"] = pd.DataFrame(catDF["670g"].sum())

                            ageANDylwSummary["isf.nDays"] = catDF["isf.min"].count()
                            ageANDylwSummary["isf.min"] = catDF["isf.min"].min()
                            ageANDylwSummary["isf.weightedMean"] = catDF["isf.weightedMean"].sum() / catDF["isf.weightedMean"].count()
                            ageANDylwSummary["isf.max"] = catDF["isf.max"].max()

                            # add cir stats
                            ageANDylwSummary["cir.nDays"] = catDF["cir.min"].count()
                            ageANDylwSummary["cir.min"] = catDF["cir.min"].min()
                            ageANDylwSummary["cir.weightedMean"] = catDF["cir.weightedMean"].sum() / catDF["cir.weightedMean"].count()
                            ageANDylwSummary["cir.max"] = catDF["cir.max"].max()

                            # add sbr stats
                            ageANDylwSummary["sbr.nDays"] = catDF["sbr.min"].count()
                            ageANDylwSummary["sbr.min"] = catDF["sbr.min"].min()
                            ageANDylwSummary["sbr.weightedMean"] = catDF["sbr.weightedMean"].sum() / catDF["sbr.weightedMean"].count()
                            ageANDylwSummary["sbr.max"] = catDF["sbr.max"].max()
                            ageANDylwSummary["sbr.nAutoMode"] = catDF["sbr.type"].count()

                            # correctionTarget stats
                            ageANDylwSummary["ct.nDays"] = catDF["ct.target.min"].count()
                            ageANDylwSummary["ct.target.min"] = catDF["ct.target.min"].min()
                            ageANDylwSummary["ct.target.weightedMean"] = catDF["ct.target.weightedMean"].sum() / catDF["ct.target.weightedMean"].count()
                            ageANDylwSummary["ct.target.max"] = catDF["ct.target.max"].max()

#                            analysisCriterion = ageANDylwSummary[((ageANDylwSummary["nDaysValidPump"]> 28) &
#                                                            (ageANDylwSummary["nDaysValidCgm"]> 28))]


                            # %% calculate local time
                            abr["date"] = pd.to_datetime(abr["utcTime"].dt.date)
                            abr = pd.merge(abr, dayData[["date", "tzo", "isDSTChangeDay"]], how="left", on="date")
                            abr["localTime"] = abr["utcTime"] + pd.to_timedelta(abr["tzo"], unit="m")

                            cgm["date"] = pd.to_datetime(cgm["utcTime"].dt.date)
                            cgm = pd.merge(cgm, dayData[["date", "tzo", "isDSTChangeDay"]], how="left", on="date")
                            cgm["localTime"] = cgm["utcTime"] + pd.to_timedelta(cgm["tzo"], unit="m")

                            bolusEvents["date"] = pd.to_datetime(bolusEvents["utcTime"].dt.date)
                            bolusEvents = pd.merge(bolusEvents, dayData[["date", "tzo", "isDSTChangeDay"]], how="left", on="date")
                            bolusEvents["localTime"] = bolusEvents["utcTime"] + pd.to_timedelta(bolusEvents["tzo"], unit="m")


                            # %% STATS PER EACH TYPE, OVERALL AND PER EACH AGE & YLW (MIN, PERCENTILES, MAX, MEAN, SD, IQR, COV)
                            # all settings

                            allSettings = pd.merge(isf.rename(columns={"isf.localTime": "localTime"}),
                                                   cir.rename(columns={"cir.localTime": "localTime"}),
                                                   how="outer", on="localTime")
                            allSettings = pd.merge(allSettings,
                                                   sbr.rename(columns={"rate": "sbr",
                                                                       "type": "sbr.type",
                                                                       "sbr.localTime": "localTime"}),
                                                   how="outer", on="localTime")
                            allSettings = pd.merge(allSettings,
                                                   correctionTarget.rename(columns={"ct.localTime": "localTime"}),
                                                   how="outer", on="localTime")
                            allSettings["hashID"] = hashID
                            allSettings["age"] = np.floor((allSettings["localTime"] - bDate).dt.days/365.25).astype(int)
                            allSettings["ylw"] = np.floor((allSettings["localTime"] - dDate).dt.days/365.25).astype(int)
                            allSettings = round_time(allSettings, timeIntervalMinutes=5,
                                                     timeField="localTime",
                                                     roundedTimeFieldName="localRoundedTime",
                                                     startWithFirstRecord=True, verbose=False)

                            colOrder = ["hashID", "age", "ylw", "localTime", "localRoundedTime",
                                        "isf", "cir", "sbr", "deviceId",
                                        "ct.low", "ct.high", "ct.target", "ct.range",
                                        "sbr.type", "isf_mmolL_U"]
                            allSettings = allSettings[colOrder]


                            fieldsToDrop = ["utcTime", "timezone", "roundedTime", "date", "tzo", "isDSTChangeDay"]
                            pumpEvents = pd.merge(abr.drop(columns=fieldsToDrop),
                                                  bolusEvents.drop(columns=fieldsToDrop),
                                                  how="outer", on="localTime")
                            pumpEvents["type"].fillna("bolus", inplace=True)
                            pumpEvents["eventType"].fillna("basal", inplace=True)
                            pumpEvents["hashID"] = hashID
                            pumpEvents["age"] = np.floor((pumpEvents["localTime"] - bDate).dt.days/365.25).astype(int)
                            pumpEvents["ylw"] = np.floor((pumpEvents["localTime"] - dDate).dt.days/365.25).astype(int)
                            pumpEvents = round_time(pumpEvents, timeIntervalMinutes=5,
                                                    timeField="localTime",
                                                    roundedTimeFieldName="localRoundedTime",
                                                    startWithFirstRecord=True, verbose=False)


                            colOrder = ["hashID", "age", "ylw", "localTime", "localRoundedTime",
                                        "rate", "durationHours",
                                        "unitsInsulin", "carbInput", "type", "eventType", "subType",
                                        "isf", "isf_mmolL_U", "insulinCarbRatio", "insulinOnBoard",
                                        "bg_mgdL", "bg_mmolL"]

                            pumpEvents = pumpEvents[colOrder]

                            cgmLite = cgm.drop(columns=fieldsToDrop)
                            cgmLite["hashID"] = hashID
                            cgmLite["age"] = np.floor((cgmLite["localTime"] - bDate).dt.days/365.25).astype(int)
                            cgmLite["ylw"] = np.floor((cgmLite["localTime"] - dDate).dt.days/365.25).astype(int)
                            cgmLite = round_time(cgmLite, timeIntervalMinutes=5,
                                                 timeField="localTime",
                                                 roundedTimeFieldName="localRoundedTime",
                                                 startWithFirstRecord=True, verbose=False)

                            colOrder = ["hashID", "age", "ylw", "localTime", "localRoundedTime",
                                        "mg_dL", "mmol_L"]

                            cgmLite = cgmLite[colOrder]


                            # %% SAVE RESULTS

                            # age and ylw stats
                            pumpEvents["rateTimesDurationHours"] = pumpEvents["rate"] * pumpEvents["durationHours"]
                            pumpEvents.rename(columns={"rate":"basalRate"}, inplace=True)
                            catDF = pumpEvents.groupby("age")

                            # actual basal rates
                            agePump = pd.DataFrame(catDF["basalRate"].count()).add_suffix(".count")
                            agePump["basalRate.min"] = catDF["basalRate"].min()
                            agePump["basalRate.weightedMean"] = catDF["rateTimesDurationHours"].sum() / catDF["durationHours"].sum()
                            agePump["basalRate.max"] = catDF["basalRate"].max()

                            # insulin events
                            insulinEvents = catDF["unitsInsulin"].describe().add_prefix("insulin.")
                            agePump = pd.concat([agePump, insulinEvents], axis=1)

                            # carbs entered in bolus calculator
                            carbEvents = catDF["carbInput"].describe().add_prefix("carb.")
                            agePump = pd.concat([agePump, carbEvents], axis=1)

                            # very low level cgm stats per age
                            catDF = cgmLite.groupby("age")
                            cgmStats = catDF["mg_dL"].describe().add_prefix("cgm.")
                            agePumpCgm = pd.concat([agePump, cgmStats], axis=1)

                            agePumpCgm.reset_index(inplace=True)

                            ageSummary = pd.merge(ageSummary, agePumpCgm, on="age", how="left")
                            ageSummary["hashID"] = hashID
                            allAgeSummaries = pd.concat([allAgeSummaries, ageSummary], ignore_index=True)

                            allAgeSummaries.to_csv(os.path.join(outputPath,
                                "allAgeSummaries-dIndex-" + str(startIndex) + ".csv"))

                            # repoeat for years living with
                            catDF = pumpEvents.groupby("ylw")
                            # actual basal rates
                            ylwPump = pd.DataFrame(catDF["basalRate"].count()).add_suffix(".count")
                            ylwPump["basalRate.min"] = catDF["basalRate"].min()
                            ylwPump["basalRate.weightedMean"] = catDF["rateTimesDurationHours"].sum() / catDF["durationHours"].sum()
                            ylwPump["basalRate.max"] = catDF["basalRate"].max()

                            # insulin events
                            insulinEvents = catDF["unitsInsulin"].describe().add_prefix("insulin.")
                            ylwPump = pd.concat([ylwPump, insulinEvents], axis=1)

                            # carbs entered in bolus calculator
                            carbEvents = catDF["carbInput"].describe().add_prefix("carb.")
                            ylwPump = pd.concat([ylwPump, carbEvents], axis=1)

                            # very low level cgm stats per age
                            catDF = cgmLite.groupby("ylw")
                            cgmStats = catDF["mg_dL"].describe().add_prefix("cgm.")
                            ylwPumpCgm = pd.concat([ylwPump, cgmStats], axis=1)

                            ylwPumpCgm.reset_index(inplace=True)

                            ylwSummary = pd.merge(ylwSummary, ylwPumpCgm, on="ylw", how="left")

                            ylwSummary["hashID"] = hashID
                            allYlwSummaries = pd.concat([allYlwSummaries, ylwSummary], ignore_index=True)

                            allYlwSummaries.to_csv(os.path.join(outputPath,
                                "allYlwSummaries-dIndex-" + str(startIndex) + ".csv"))


                            # repoeat for agne AND years living with
                            catDF = pumpEvents.groupby(["age", "ylw"])
                            # actual basal rates
                            ageANDylwPump = pd.DataFrame(catDF["basalRate"].count()).add_suffix(".count")
                            ageANDylwPump["basalRate.min"] = catDF["basalRate"].min()
                            ageANDylwPump["basalRate.weightedMean"] = catDF["rateTimesDurationHours"].sum() / catDF["durationHours"].sum()
                            ageANDylwPump["basalRate.max"] = catDF["basalRate"].max()

                            # insulin events
                            insulinEvents = catDF["unitsInsulin"].describe().add_prefix("insulin.")
                            ageANDylwPump = pd.concat([ageANDylwPump, insulinEvents], axis=1)

                            # carbs entered in bolus calculator
                            carbEvents = catDF["carbInput"].describe().add_prefix("carb.")
                            ageANDylwPump = pd.concat([ageANDylwPump, carbEvents], axis=1)

                            # very low level cgm stats per age
                            catDF = cgmLite.groupby(["age", "ylw"])
                            cgmStats = catDF["mg_dL"].describe().add_prefix("cgm.")
                            ageANDylwPumpCgm = pd.concat([ageANDylwPump, cgmStats], axis=1)

                            ageANDylwSummary = ageANDylwSummary.join(ageANDylwPumpCgm, how="left")

                            ageANDylwPumpCgm.reset_index(inplace=True)
                            ageANDylwSummary.reset_index(inplace=True)

                            ageANDylwSummary["hashID"] = hashID
                            allAgeANDylwSummaries = pd.concat([allAgeANDylwSummaries, ageANDylwSummary], ignore_index=True)

                            allAgeANDylwSummaries.to_csv(os.path.join(outputPath,
                                "allAgeANDylwSummaries-dIndex-" + str(startIndex) + ".csv"))


                             # %% save data for this person
                            outputString = "age-%s-%s-ylw-%s-%s-lp-%s-670g-%s-id-%s"
                            outputFormat = (f"{minAge:02d}",
                                            f"{maxAge:02d}",
                                            f"{minYLW:02d}",
                                            f"{maxYLW:02d}",
                                            f"{int(nDaysClosedLoop):03d}",
                                            f"{int(n670gDays):03d}",
                                            hashID[0:4])
                            outputFolderName = outputString % outputFormat
                            outputFolderName_Path = os.path.join(outputPath, "data", outputFolderName)
                            if not os.path.exists(outputFolderName_Path):
                                os.makedirs(outputFolderName_Path)

                            fName = outputFolderName + "-allSettings.csv"
                            allSettings.to_csv(os.path.join(outputFolderName_Path, fName))
                            fName = outputFolderName + "-pumpEvents.csv"
                            pumpEvents.to_csv(os.path.join(outputFolderName_Path, fName))
                            fName = outputFolderName + "-cgmLite.csv"
                            cgmLite.to_csv(os.path.join(outputFolderName_Path, fName))



                            # %% save the processed data (saving this data will take up a lot of space and time)
                            data.to_csv(os.path.join(processedDataPath, "allDataCleaned-PHI-" + userID + ".csv"))
                            basal.to_csv(os.path.join(processedDataPath, "basal-PHI-" + userID + ".csv"))
                            bolus.to_csv(os.path.join(processedDataPath, "bolus-PHI-" + userID + ".csv"))
                            cgmData.to_csv(os.path.join(processedDataPath, "cgm-PHI-" + userID + ".csv"))
                            pumpSettings.to_csv(os.path.join(processedDataPath, "pumpSettings-PHI-" + userID + ".csv"))

                        else:
                            metadata["flags"] = "no bolus wizard data"
                    else:
                        metadata["flags"] = "missing either pump or cgm  data"
                else:
                    metadata["flags"] = "file contains no data"
            else:
                metadata["flags"] = "file does not exist"
        else:
            metadata["flags"] = "missing bDay/dDay"

    except:
        print("something is broke dIndex=", dIndex)
        metadata["flags"] = "something is broke"


    # write metaData to allMetadata
    allMetadata = pd.concat([allMetadata, metadata], axis=0, sort=True)
    allMetadata.to_csv(os.path.join(outputPath,
        "allMetadata-dIndex-" + str(startIndex) + ".csv"))

    print("done with", dIndex)


# %% V2 DATA TO GRAB
# THERE IS AN ISSUE WITH COUNTING 670G SETTINGS
# ADD ROUNDEDLOCAL TIME TO THE END RESULTS
# CALCULATE MMOL SUMMARIES
# GET RID OF ROUNDING TIME AT THE BEGINNING
# DEFINE A DAY BETWEEN 6AM AND 6AM
# EXPAND THE CORRECTION TIME VALUES TO BE UNIFORM ACROSS ALL USERS AND DEVICES
# FIX DAYLIGHT SAVINGS TIME TIMES
# FIGURE OUT WHY TEMP BASAL COUNTS ARE DIFFERENT BETWEEN THE TWO DIFFERENT METHODS
# MAX BASAL RATE, MAX BOLUS AMOUNT, AND INSULIN DURATION SET ON SELECT PUMPS
# ALERT SETTINGS
# ESTIMATED LOCAL TIME
# PUMP AND CGM DEVICE ()
# GLYCEMIC OUTCOMES
# DO NOT ROUND DATA
# INFUSION SITE CHANGES
# CGM CALIBRATIONS
