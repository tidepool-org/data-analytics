#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: qualify donated datasets
version: 0.0.1
created: 2018-02-21
author: Ed Nykaza
dependencies:
    *
license: BSD-2-Clause
TODO:
* [] account for 15 minute libre data, most likely change will be to change
timeFreqMin to 15, but it could affect the number of
boluses per day...HOWEVER, THIS CAN BE AVOIDED IF WE CHANGE FROM MERGING AT THE
5 OR 15 MINUTE LEVEL, AND RATHER MERGE AT THE DAY LEVEL.
* [] add version number to the qualification results so that we can keep track
of which qualification scripts were used to qualify the datasets. Figure out
how to get version number from the header
* [] get the description from the header and add to argparse
* [] add everything up to the contiguous data to the flatten-json script, and
start this file at the point of loading the contiguous data, it should
significantly speed up the qualification process
* [] update variable names to be shorter and possibily more descriptive
* [] update readme file
"""

# %% REQUIRED LIBRARIES
import pandas as pd
import datetime as dt
import numpy as np
import os
import sys
import argparse
import json

# %% USER INPUTS
codeDescription = "Qualify donated datasets"

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
                    default="../data/",
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

parser.add_argument("-q",
                    "--qualification-criteria",
                    dest="qualificationCriteria",
                    default="./tidepool-qualification-criteria.json",
                    type=argparse.FileType('r'),
                    help="JSON file to be processed, see " +
                         "tidepool-qualification-critier.json " +
                         "for a list of required fields")

args = parser.parse_args()


# %% FUNCTIONS
def defineStartAndEndIndex(args):
    startIndex = int(args.startIndex)
    endIndex = int(args.endIndex)
    if endIndex == -1:
        if startIndex == 0:
            endIndex = len(uniqueDonors)
        else:
            endIndex = startIndex + 1

    return startIndex, endIndex


def removeNegativeDurations(df):
    if "duration" in list(df):
        nNegativeDurations = sum(df.duration < 0)
        if nNegativeDurations > 0:
            df = df[~(df.duration < 0)]

    return df, nNegativeDurations


def filterAndSort(groupedDF, filterByField, sortByField):
    filterDF = groupedDF.get_group(filterByField).dropna(axis=1, how="all")
    filterDF = filterDF.sort_values(sortByField)
    return filterDF


def getClosedLoopDays(df, nTempBasalsPerDayIsClosedLoop):

    tbDataFrame = df.loc[df.deliveryType == "temp", ["time"]]
    tbDataFrame.index = pd.to_datetime(tbDataFrame["time"])
    tbDataFrame = tbDataFrame.drop(["time"], axis=1)
    tbDataFrame["basal.temp.count"] = 1
    nTempBasalsPerDay = tbDataFrame.resample("D").sum()
    closedLoopDF = pd.DataFrame(nTempBasalsPerDay,
                                index=nTempBasalsPerDay.index.date)
    closedLoopDF["date"] = nTempBasalsPerDay.index.date
    closedLoopDF["basal.closedLoopDays"] = \
        closedLoopDF["basal.temp.count"] >= nTempBasalsPerDayIsClosedLoop

    return closedLoopDF, closedLoopDF["basal.closedLoopDays"].sum()


def removeInvalidCgmValues(df):
    nBefore = len(df)
    df = df.query("(value >= 2.109284236597303) and" +
                  "(value <= 22.314006924003046)")
    nRemoved = nBefore - len(df)
    return df, nRemoved


def roundTimeAndDropDups(df, timeInterval):
    df["roundedTime"] = \
        pd.DatetimeIndex(df["time"]).round(str(timeInterval) + "min")

    nBefore = len(df)
    df = df.loc[~df["roundedTime"].duplicated()]
    df = df.reset_index(drop=True)
    nDuplicatesRemoved = nBefore - len(df)
    return df, nDuplicatesRemoved


def getStartAndEndTimes(df):
    dfBeginDate = df.roundedTime.min()
    dfEndDate = df.roundedTime.max()
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


def getDayStats(df, closedLoopDF):
    # group df by Day
    catDF = df.groupby(df["dayIndex"])

    # get stats
    cgmRecordsPerDay = catDF.cgm_mmol_L.count()
    bolusRecordsPerDay = catDF.bolus.count()
    dayDate = catDF.dayIndex.describe()["top"]
    dexcomCGM = catDF.dexcomCGM.describe()["top"]
    nTypesCGM = catDF.dexcomCGM.describe()["unique"]
    dexcomOnlyPerDay = (dexcomCGM & (nTypesCGM == 1))

    dfStats = pd.DataFrame({"date": dayDate,
                            "bolus.count": bolusRecordsPerDay,
                            "cgm.count": cgmRecordsPerDay,
                            "cgm.dexcomOnly": dexcomOnlyPerDay})

    dfStats = dfStats.reset_index(drop=True)

    # add in closedLoopDays
    dfStats = pd.merge(dfStats, closedLoopDF, how="left", on="date")

    return dfStats


def dexcomCriteria(df):
    # if day is closed loop or non-dexcom set to 0
    isClosedLoop = (df["basal.closedLoopDays"].fillna(False))
    isNonDexcom = ~(df["cgm.dexcomOnly"])
    df.loc[(isClosedLoop | isNonDexcom),
           ["bolus.count", "cgm.count"]] = 0

    return df


def isQualifyingDay(df, bolusCriteria, percentCgmCriteria, cgmPoints1Day):
    df["cgm.percentage"] = df["cgm.count"] / cgmPoints1Day
    df["qualifyingDay"] = ((df["bolus.count"] >= bolusCriteria) &
                           (df["cgm.percentage"] >= percentCgmCriteria))

    # calculate the gaps in the data and group them
    df["nonQualifyingDay"] = ~df["qualifyingDay"]
    df["qualifyAndNotQualifyGroups"] = \
        ((df.qualifyingDay != df.qualifyingDay.shift()).cumsum())
    df["gapGroup"] = df["qualifyAndNotQualifyGroups"] * df["nonQualifyingDay"]

    return df


def getSummaryStats(df, dayStatsDF):
    df["contiguous.maxCgmPercentage"] = dayStatsDF["cgm.percentage"].max()

    numberQualifyingDays = dayStatsDF.qualifyingDay.sum()
    df["qualifyingDays.count"] = numberQualifyingDays

    numberContiguousDays = len(dayStatsDF)
    df["contiguous.count"] = numberContiguousDays

    percentQualifyingDays = round((numberQualifyingDays /
                                   numberContiguousDays) * 100, 1)
    df["qualifyingDays.percent"] = percentQualifyingDays

    avgBolusRecordsQualfiyingDays = \
        round(dayStatsDF.loc[dayStatsDF.qualifyingDay == 1,
                             "bolus.count"].mean(), 1)

    df["qualfiyingDays.avgBolusCount"] = avgBolusRecordsQualfiyingDays

    return df


def getQualifyingTier(df, criteriaName, contDayCriteria,
                      avgBolusCountCriteria, percQualDayCriteria,
                      maxGapToContRatioCriteria):

    tempDF = pd.DataFrame(columns=["avgBolusRecordsPerDay",
                                   "numberContiguousDays",
                                   "percentQualifyingDays",
                                   "maxGapToContiguousRatio",
                                   "tier"])

    for i in range(0, len(df)-(contDayCriteria-1)):

        tempIndex = min(i+contDayCriteria, len(df))

        numberContiguousDays = df["bolus.count"].iloc[i:tempIndex].count()
        tempDF.loc[i, "numberContiguousDays"] = numberContiguousDays

        avgBolusRecordsPerDay = df["bolus.count"].iloc[i:tempIndex].mean()
        tempDF.loc[i, "avgBolusRecordsPerDay"] = avgBolusRecordsPerDay

        percentQualifyingDays = \
            df.qualifyingDay.iloc[i:tempIndex].sum() / contDayCriteria * 100
        tempDF.loc[i, "percentQualifyingDays"] = percentQualifyingDays

        gapGroups = \
            df.gapGroup.iloc[i:tempIndex].loc[df.gapGroup > 0].astype(str)

        if len(gapGroups) > 0:
            maxGapToContiguousRatio = \
                gapGroups.describe()["freq"] / contDayCriteria * 100
        else:
            maxGapToContiguousRatio = 0

        tempDF.loc[i, "maxGapToContiguousRatio"] = maxGapToContiguousRatio

        tier = (numberContiguousDays == contDayCriteria
                and avgBolusRecordsPerDay >= avgBolusCountCriteria
                and percentQualifyingDays >= percQualDayCriteria
                and maxGapToContiguousRatio <= maxGapToContRatioCriteria)

        tempDF.loc[i, "tier"] = tier

    df = pd.concat([df, tempDF.add_prefix(criteriaName + ".")], axis=1)

    # if the dataset qualified
    tierName = criteriaName + "." + "tier"
    if sum(df[tierName].fillna(0) * 1) > 0:
        tierGroupName = criteriaName + ".group"
        tierGapGroupName = criteriaName + ".gapGroup"
        df[tierGroupName] = ((df[tierName] != df[tierName].shift()).cumsum())
        df[tierGapGroupName] = df[tierGroupName] * df[tierName]
        groupObj = df[df[tierGapGroupName] > 0].groupby(tierGapGroupName)
        biggestGroup = groupObj[tierGroupName].count().idxmax()
        qualifiedBeginDate = groupObj.get_group(biggestGroup).date.min()
        qualifiedEndDate = \
            groupObj.get_group(biggestGroup).date.max() + \
            pd.Timedelta(days=contDayCriteria)
        nDaysToDeliever = (qualifiedEndDate - qualifiedBeginDate).days
        qualifyingResults = {"qualified": True,
                             "qualified.beginDate": qualifiedBeginDate,
                             "qualified.endDate": qualifiedEndDate,
                             "qualified.nDaysToDeliever": nDaysToDeliever}
    else:
        qualifyingResults = {"qualified": False}

    return df, qualifyingResults


def qualify(df, metaDF, q, idx):
    q["maxGapToContigRatio"]
    metaDF[q["tierAbbr"] + ".topTier"] = q["tierAbbr"] + "0"
    for j in range(0, len(q["tierNames"])):
        df, qualifyingResults = \
            getQualifyingTier(df,
                              q["tierNames"][j],
                              q["minContiguousDays"][j],
                              q["avgBolusesPerDay"][j],
                              q["percentDaysQualifying"][j],
                              q["maxGapToContigRatio"][j])

        qrDF = pd.DataFrame(qualifyingResults, index=[idx]). \
            add_prefix(q["tierNames"][j] + ".")

        metaDF = pd.concat([metaDF, qrDF], axis=1)
        if qualifyingResults["qualified"]:
            metaDF[q["tierAbbr"] + ".topTier"] = \
                q["tierNames"][j]

    return df, metaDF


# %% GLOBAL VARIABLES
qualifiedOn = dt.datetime.now().strftime("%Y-%m-%d")
phiDateStamp = "PHI-" + args.dateStamp

qualCriteria = json.load(args.qualificationCriteria)

criteriaMaxCgmPointsPerDay = \
    1440 / qualCriteria["timeFreqMin"]

# input folder(s)
donorFolder = os.path.join(args.dataPath, phiDateStamp + "-donor-data")
if not os.path.isdir(donorFolder):
    sys.exit("{0} is not a directory".format(donorFolder))

donorCsvFolder = os.path.join(donorFolder,
                              phiDateStamp + "-donorCsvFolder", "")
if not os.path.isdir(donorCsvFolder):
    sys.exit("{0} is not a directory".format(donorCsvFolder))

# create output folder(s)
donorQualifyFolder = os.path.join(donorFolder,
                                  args.dateStamp + "-qualified", "")
if not os.path.exists(donorQualifyFolder):
    os.makedirs(donorQualifyFolder)

# load in list of unique donors
donorPath = os.path.join(donorFolder, phiDateStamp + "-uniqueDonorList.csv")
uniqueDonors = pd.read_csv(donorPath, index_col="dIndex")

allMetaData = pd.DataFrame()

# define start and end index
startIndex, endIndex = defineStartAndEndIndex(args)


# %% START OF CODE
# loop through each donor
for dIndex in range(startIndex, endIndex):

    # load in all data for user
    metadata = pd.DataFrame(index=[dIndex])
    userID = uniqueDonors.loc[dIndex, "userID"]
    csvFileName = os.path.join(donorCsvFolder, "PHI-" + userID + ".csv")
    if os.path.exists(csvFileName):
        phiUserID = "PHI-" + userID
        data = pd.read_csv(os.path.join(donorCsvFolder, phiUserID + ".csv"),
                           low_memory=False)

        if (("cbg" in data.type.unique()) and ("bolus" in data.type.unique())):

            # get rid of all negative durations
            data, numberOfNegativeDurations = removeNegativeDurations(data)
            metadata["all.negativeDurationsRemoved.count"] = \
                numberOfNegativeDurations

            # group data by type
            groupedData = data.groupby(by="type")

            # %% BASAL
            # filter by basal data and sort by time
            if "basal" in data.type.unique():
                basalData = filterAndSort(groupedData, "basal", "time")

                # get closed loop days
                nTB = qualCriteria["nTempBasalsPerDayIsClosedLoop"]
                closedLoopDays, nClosedLoopDays = getClosedLoopDays(basalData,
                                                                    nTB)

            else:
                closedLoopDays = np.nan
                nClosedLoopDays = np.nan

            metadata["basal.closedLoopDays.count"] = nClosedLoopDays

            # %% CGM
            # filter by cgm and sort by time
            cgmData = filterAndSort(groupedData, "cbg", "time")

            # get rid of cbg values too low/high (< 38 & > 402 mg/dL)
            cgmData, numberOfInvalidCgmValues = removeInvalidCgmValues(cgmData)
            metadata["cgm.invalidValues.count"] = numberOfInvalidCgmValues

            # round time to nearest timeFreqMin
            # and get rid of duplicates
            cgmData, nDuplicates = \
                roundTimeAndDropDups(cgmData,
                                     qualCriteria["timeFreqMin"])
            metadata["cgm.duplicatesRemoved.count"] = nDuplicates

            # get start and end times
            cgmBeginDate, cgmEndDate = getStartAndEndTimes(cgmData)
            metadata["cgm.beginDate"] = cgmBeginDate
            metadata["cgm.endDate"] = cgmEndDate

            # get a list of dexcom cgms
            cgmData, percentDexcom = getListOfDexcomCGMDays(cgmData)
            metadata["cgm.percentDexcomCGM"] = percentDexcom

            # drop columns that are not needed for qualification
            cgmData = cgmData[["value",
                               "roundedTime",
                               "dexcomCGM"]].rename(columns={
                                   "value": "cgm_mmol_L"})

            # %% BOLUS
            # filter by bolus and sort by time
            bolusData = filterAndSort(groupedData, "bolus", "time")

            # round time to nearest timeFreqMin
            # and get rid of duplicates
            bolusData, nDuplicates = \
                roundTimeAndDropDups(bolusData,
                                     qualCriteria["timeFreqMin"])
            metadata["bolus.duplicatesRemoved.count"] = nDuplicates

            # get start and end times
            bolusBeginDate, bolusEndDate = getStartAndEndTimes(bolusData)
            metadata["bolus.beginDate"] = bolusBeginDate
            metadata["bolus.endDate"] = bolusEndDate

            # drop columns that are not needed for qualification
            bolusData = bolusData[["roundedTime",
                                   "subType"]].rename(columns={
                                       "subType": "bolus"})

            # %% CONTIGUOUS DATA
            # calculate the start and end of contiguous data
            contiguousBeginDate = max(cgmBeginDate, bolusBeginDate)
            contiguousEndDate = min(cgmEndDate, bolusEndDate)
            metadata["contiguous.beginDate"] = contiguousBeginDate
            metadata["contiguous.endDate"] = contiguousEndDate

            # create a dataframe over the contiguous time series
            rng = pd.date_range(contiguousBeginDate,
                                contiguousEndDate,
                                freq=str(qualCriteria["timeFreqMin"]) + "min")
            contiguousData = pd.DataFrame(rng, columns=["roundedTime"])
            contiguousData = pd.merge(contiguousData, bolusData,
                                      on="roundedTime", how="left")
            contiguousData = pd.merge(contiguousData, cgmData,
                                      on="roundedTime", how="left")

            if ((len(contiguousData) > 0) &
               (contiguousData.cgm_mmol_L.count() > 0) &
               (contiguousData.bolus.count() > 0)):

                contiguousData["dayIndex"] = contiguousData.roundedTime.dt.date

                # create an output folder
                userQualifyFolder = os.path.join(donorQualifyFolder, userID)
                if not os.path.exists(userQualifyFolder):
                    os.makedirs(userQualifyFolder)

                # %% QUALIFICATION AT DAY LEVEL
                # calculate day stats
                dayStats = getDayStats(contiguousData, closedLoopDays)

                # dexcom specific qualification criteria
                if qualCriteria["name"] == "dexcom":
                    dayStats = dexcomCriteria(dayStats)

                # determine if each day qualifies
                dayStats = \
                    isQualifyingDay(dayStats,
                                    qualCriteria["bolusesPerDay"],
                                    qualCriteria["cgmPercentPerDay"],
                                    criteriaMaxCgmPointsPerDay)
                # calcuate summary stats
                metadata = getSummaryStats(metadata, dayStats)

                # %% QUALIFICATION OF DATASET
                dayStats, metadata = qualify(dayStats, metadata,
                                             qualCriteria, dIndex)

                # %% SAVE RESULTS
                dayStats.index.name = "dayIndex"
                dSFileName = os.path.join(
                    userQualifyFolder, userID + "-" + "qualified-as-" +
                    metadata[qualCriteria["tierAbbr"] + ".topTier"].values[0] +
                    "-on-" + qualifiedOn + "-for-" + qualCriteria["name"] +
                    "-dayStats.csv")

                dayStats.to_csv(dSFileName)

                # append meta data to the user results
                allMetaData = pd.concat([allMetaData, metadata], axis=0)

                # update on progress
                print(round((dIndex - startIndex + 1) /
                            (endIndex - startIndex) * 100, 1),
                      "% ", dIndex, "of", endIndex - 1, "qualifed as:",
                      metadata[qualCriteria["tierAbbr"] +
                               ".topTier"].values)

allMetaData.index.name = "dIndex"
uniqueDonors = pd.concat([uniqueDonors, allMetaData], axis=1)
aMFileName = os.path.join(donorFolder,
                          phiDateStamp + "-qualified-on-" + qualifiedOn +
                          "-for-" + qualCriteria["name"] + "-metadata.csv")

uniqueDonors.to_csv(aMFileName)
