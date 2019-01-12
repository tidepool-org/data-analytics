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
import os
import pdb


# %% USER INPUTS (ADD THIS IN LATER)
#codeDescription = "Get user's settings and events"
#parser = argparse.ArgumentParser(description=codeDescription)


# %% FUNCTIONS

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
    removeFields = ["suppressed",
                    "recommended",
                    "payload"]

    tempRemoveFields = list(set(df) & set(removeFields))
    tempDf = df[tempRemoveFields]
    df = df.drop(columns=tempRemoveFields)

    return df, tempDf


def flattenJson(df):

    # remove fields that we don't want to flatten
    df, holdData = tempRemoveFields(df)

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
    return df, percentDexcomCGM


def load_csv(dataPathAndName):
    df = pd.read_csv(dataPathAndName, low_memory=False)
    return df


def load_json(dataPathAndName):
    df = pd.read_json(dataPathAndName, orient="records")
    return df


# %% LOAD IN ONE FILE, BUT EVENTUALLY THIS WILL LOOOP THROUGH ALL USER'S
dataPulledDate = "2018-09-28"
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

allMetadata = donors[['hashID', 'diagnosisType']].copy()

# %% MAKE THIS A FUNCTION SO THAT IT CAN BE RUN PER EACH INDIVIDUAL

# this is where the loop will go:
for dIndex in range(0, len(donors)):

    # clear output dataframes
    isf, cir, correctionTarget = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # %% ID, HASHID, AGE, & YLW
    userID = donors.userID[dIndex]
    hashID = donors.hashID[dIndex]
    metadata = pd.DataFrame(index=[dIndex])
    metadata["hashID"] = hashID

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
                data = flattenJson(data)


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

                    commonColumnHeadings = ["hashID",
                                            "age",
                                            "ylw"]


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

                        # isf and cir associated with bolus event
                        if "insulinSensitivities" in list(bolus):
                            pdb.set_trace()

                        if "carbRatios" in list(bolus):
                            pdb.set_trace()

                        bolus["isf_mmolL_U"] = bolus["insulinSensitivity"]
                        bolus["isf"] = mmolL_to_mgdL(bolus["isf_mmolL_U"])

                        bolusCH = commonColumnHeadings.copy()
                        bolusCH.extend(["utcTime", "roundedTime", "normal", "carbInput", "subType",
                                        "insulinOnBoard", "bgInput",
                                        "isf", "isf_mmolL_U", "insulinCarbRatio"])
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
                            bolusExtendedCH = commonColumnHeadings.copy()
                            bolusExtendedCH.extend(["utcTime", "roundedTime", "durationHours", "rate",  "type"])
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

                        # ISF
                        isfColHeadings = commonColumnHeadings.copy()
                        isfColHeadings.extend(["isf.time", "isf", "isf_mmolL_U"])

                        if "insulinSensitivity.amount" in list(pumpSettings):
                            isfColHead = "insulinSensitivity"
                            pumpSettings["isf_mmolL_U"] = pumpSettings[isfColHead + ".amount"]
                            pumpSettings["isf"] = mmolL_to_mgdL(pumpSettings["isf_mmolL_U"])
                            pumpSettings["isf.time"] = pd.to_datetime(pumpSettings["day"]) + \
                                pd.to_timedelta(pumpSettings[isfColHead + ".start"], unit="ms")

                            isf = pumpSettings.loc[pumpSettings["isf"].notnull(), isfColHeadings]
                        else:
                            isfColHead = "insulinSensitivities"
                            isf = pd.DataFrame(columns=isfColHeadings)

                            # edge case where active schedule is a float


                            for p, actSched in zip(pumpSettings.index, pumpSettings["activeSchedule"]):
                                # edge case where actSchedule is float
                                if isinstance(actSched, float):
                                    actSched = str(int(actSched))

                                tempDF = pd.DataFrame(pumpSettings.loc[p, isfColHead + "." + actSched])
                                tempDF["day"] = pumpSettings.loc[p, "day"]
                                tempDF["isf.time"] = pd.to_datetime(tempDF["day"]) + pd.to_timedelta(tempDF["start"], unit="ms")
                                tempDF["hashID"] = pumpSettings.loc[p, "hashID"]
                                tempDF["age"] = pumpSettings.loc[p, "age"]
                                tempDF["ylw"] = pumpSettings.loc[p, "ylw"]
                                tempDF["isf_mmolL_U"] = tempDF["amount"]
                                tempDF["isf"] = mmolL_to_mgdL(tempDF["isf_mmolL_U"])
                                isf = pd.concat([isf, tempDF[isfColHeadings]], ignore_index=True)

                        # CIR
                        cirColHeadings = commonColumnHeadings.copy()
                        cirColHeadings.extend(["cir.time", "cir"])

                        if "carbRatio.amount" in list(pumpSettings):
                            cirColHead = "carbRatio"
                            pumpSettings["cir"] = pumpSettings[cirColHead + ".amount"]
                            pumpSettings["cir.time"] = pd.to_datetime(pumpSettings["day"]) + \
                                pd.to_timedelta(pumpSettings[cirColHead + ".start"], unit="ms")

                            cir = pumpSettings.loc[pumpSettings["carbRatio.amount"].notnull(), cirColHeadings]
                        else:
                            cirColHead = "carbRatios"
                            cir = pd.DataFrame(columns=cirColHeadings)
                            for p, actSched in zip(pumpSettings.index, pumpSettings["activeSchedule"]):
                                # edge case where actSchedule is float
                                if isinstance(actSched, float):
                                    actSched = str(int(actSched))
                                tempDF = pd.DataFrame(pumpSettings.loc[p, cirColHead + "." + actSched])
                                tempDF["day"] = pumpSettings.loc[p, "day"]
                                tempDF["cir.time"] = pd.to_datetime(tempDF["day"]) + pd.to_timedelta(tempDF["start"], unit="ms")
                                tempDF["hashID"] = pumpSettings.loc[p, "hashID"]
                                tempDF["age"] = pumpSettings.loc[p, "age"]
                                tempDF["ylw"] = pumpSettings.loc[p, "ylw"]
                                tempDF["cir"] = tempDF["amount"].astype(float)
                                cir = pd.concat([cir, tempDF[cirColHeadings]], ignore_index=True)


                        # CORRECTION TARGET
                        ctColHeadings = commonColumnHeadings.copy()
                        ctColHeadings.extend(["ct.time", "ct.low", "ct.high", "ct.target", "ct.range"])

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

                            pumpSettings["ct.time"] = pd.to_datetime(pumpSettings["day"]) + \
                                pd.to_timedelta(pumpSettings[ctColHead + "start"], unit="ms")

                            correctionTarget = pumpSettings.loc[pumpSettings["bgTarget.start"].notnull(), ctColHeadings]

                        else:
                            ctColHead = "bgTargets"
                            correctionTarget = pd.DataFrame(columns=ctColHeadings)
                            for p, actSched in zip(pumpSettings.index, pumpSettings["activeSchedule"]):
                                # edge case where actSchedule is float
                                if isinstance(actSched, float):
                                    actSched = str(int(actSched))
                                tempDF = pd.DataFrame(pumpSettings.loc[p, ctColHead + "." + actSched])
                                tempDF["day"] = pumpSettings.loc[p, "day"]
                                tempDF["ct.time"] = pd.to_datetime(tempDF["day"]) + pd.to_timedelta(tempDF["start"], unit="ms")
                                tempDF["hashID"] = pumpSettings.loc[p, "hashID"]
                                tempDF["age"] = pumpSettings.loc[p, "age"]
                                tempDF["ylw"] = pumpSettings.loc[p, "ylw"]
                                for targetType in ["low", "high", "target", "range"]:
                                    if targetType in list(tempDF):
                                        tempDF["ct." + targetType + "_mmolL"] = \
                                            tempDF[targetType]

                                        tempDF["ct." + targetType] = \
                                            mmolL_to_mgdL(tempDF["ct." + targetType + "_mmolL"])
                                    else:
                                        tempDF["ct." + targetType + "_mmolL"] = np.nan
                                        tempDF["ct." + targetType]  = np.nan

                                correctionTarget = pd.concat([correctionTarget, tempDF[ctColHeadings]], ignore_index=True)

                        # SCHEDULED BASAL RATES
                        sbrColHeadings = commonColumnHeadings.copy()
                        sbrColHeadings.extend(["sbrTime", "rate", "type"])
                        sbr = pd.DataFrame(columns=sbrColHeadings)
                        for p, actSched in zip(pumpSettings.index, pumpSettings["activeSchedule"]):
                            # edge case where actSchedule is float
                            if isinstance(actSched, float):
                                actSched = str(int(actSched))
                            if 'Auto Mode' not in actSched:
                                tempDF = pd.DataFrame(pumpSettings.loc[p, "basalSchedules." + actSched])
                                tempDF["day"] = pumpSettings.loc[p, "day"]
                                tempDF["type"] = np.nan
                                tempDF["sbrTime"] = pd.to_datetime(tempDF["day"]) + pd.to_timedelta(tempDF["start"], unit="ms")
                            else:
                                tempDF = pd.DataFrame(index=[0])
                                tempDF["sbrTime"] = np.nan
                                tempDF["rate"] = np.nan
                                tempDF["type"] = "AutoMode"

                            tempDF["hashID"] = pumpSettings.loc[p, "hashID"]
                            tempDF["age"] = pumpSettings.loc[p, "age"]
                            tempDF["ylw"] = pumpSettings.loc[p, "ylw"]
                            sbr = pd.concat([sbr, tempDF[sbrColHeadings]], ignore_index=True)

                        # max basal rate, max bolus amount, and insulin duration
                        if "rateMaximum" in list(data):
                            pdb.set_trace()
                        if "amountMaximum" in list(data):
                            pdb.set_trace()
                        if "bolus.calculator" in list(data):
                            pdb.set_trace()


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
                        abrColHeadings = commonColumnHeadings.copy()
                        abrColHeadings.extend(["utcTime", "roundedTime", "durationHours", "rate", "type"])
                        abr = basal[abrColHeadings]
                        if "duration" in list(bolus):
                            abr = pd.concat([abr, bolusExtendedEvents], ignore_index=True)
                            abr.sort_values("utcTime", inplace=True)

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
                        cgmColHeadings = commonColumnHeadings.copy()
                        cgmColHeadings.extend(["utcTime", "roundedTime", "value"])

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
                        ageSummary["nDaysclosedLopp"] = pd.DataFrame(catDF["basal.closedLoopDays"].sum())
                        ageSummary["n670gDays"] = pd.DataFrame(catDF["670g"].sum())
                        ageSummary.reset_index(inplace=True)

                        catDF = dayData.groupby("ylw")
                        ylwSummary = pd.DataFrame(catDF.validPumpData.sum())
                        ylwSummary.rename(columns={"validPumpData": "nDaysValidPump"}, inplace=True)
                        ylwSummary["nDaysValidCgm"] = pd.DataFrame(catDF.validCGMData.sum())
                        ylwSummary["nDaysclosedLopp"] = pd.DataFrame(catDF["basal.closedLoopDays"].sum())
                        ylwSummary["n670gDays"] = pd.DataFrame(catDF["670g"].sum())
                        ylwSummary.reset_index(inplace=True)

                        # %% STATS PER EACH TYPE, OVERALL AND PER EACH AGE & YLW (MIN, PERCENTILES, MAX, MEAN, SD, IQR, COV)





                        # %% SAVE RESULTS


                        # save the processed data
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
        metadata["flags"] = "fmissing bDay/dDay"

    # write metaData to allMetadata
    allMetadata = pd.merge(allMetadata, metadata, how="left", on="hashID")
    allMetadata.to_csv(os.path.join(outputPath, "allMetadata.csv"))

    print("done with", dIndex)


# %% V2 DATA TO GRAB
# FIGURE OUT WHY TEMP BASAL COUNTS ARE DIFFERENT BETWEEN THE TWO DIFFERENT METHODS
# MAX BASAL RATE, MAX BOLUS AMOUNT, AND INSULIN DURATION SET ON SELECT PUMPS
# ALERT SETTINGS
# ESTIMATED LOCAL TIME
# PUMP AND CGM DEVICE ()
# GLYCEMIC OUTCOMES
# DO NOT ROUND DATA
# INFUSION SITE CHANGES
# CGM CALIBRATIONS
