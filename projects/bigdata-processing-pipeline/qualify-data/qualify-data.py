#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: Qualify Tidepool Datasets
version: 0.0.1
created: 2018-02-21
author: Ed Nykaza
dependencies:
    * this requires the tidals package, which is automatically downloaded when
you load in the tidepool data analytics development (tda-dev) environment

license: BSD-2-Clause

TODO:
* [] make saving the metadata optional, and by default to no
"""


# %% REQUIRED LIBRARIES
import os
import sys
import argparse
import json
import pandas as pd
import datetime as dt
import importlib
# load tidals package locally if it does not exist globally
if importlib.util.find_spec("tidals") is None:
    tidalsPath = os.path.abspath(
                    os.path.join(
                    os.path.dirname(__file__),
                    "..", "..", "tidepool-analysis-tools"))
    if tidalsPath not in sys.path:
        sys.path.insert(0, tidalsPath)
import tidals as td


# %% USER INPUTS
codeDescription = "Qualify Tidepool datasets"

parser = argparse.ArgumentParser(description=codeDescription)

parser.add_argument("-d",
                    "--date-stamp",
                    dest="dateStamp",
                    default=dt.datetime.now().strftime("%Y-%m-%d"),
                    help="date in '%Y-%m-%d' format needed to call unique " +
                    "donor list (e.g., PHI-2018-03-02-uniqueDonorList)")

parser.add_argument("-o",
                    "--output-data-path",
                    dest="dataPath",
                    default=os.path.abspath(
                            os.path.join(
                            os.path.dirname(__file__), "..", "data")),
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
                    help="donor index (integer) to end at," +
                    "-1 will result in 1 file if startIndex != 0," +
                    "and will default to number of unique donors" +
                    "if startIndex = 0, or endIndex = -2")

parser.add_argument("-q",
                    "--qualification-criteria",
                    dest="qualificationCriteria",
                    default=os.path.abspath(
                            os.path.join(
                            os.path.dirname(__file__),
                            "tidepool-qualification-criteria.json")),
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
    if endIndex == -2:
        endIndex = len(uniqueDonors)
    return startIndex, endIndex


def removeNegativeDurations(df):
    if "duration" in list(df):
        nNegativeDurations = sum(df.duration < 0)
        if nNegativeDurations > 0:
            df = df[~(df.duration < 0)]

    return df, nNegativeDurations


def addUploadDate(df):
    uploadTimes = pd.DataFrame(df[df.type == "upload"].groupby("uploadId").time.describe()["top"])
    uploadTimes.reset_index(inplace=True)
    uploadTimes.rename(columns={"top": "uploadTime"}, inplace=True)
    df = pd.merge(df, uploadTimes, how='left', on='uploadId')

    return df


def filterAndSort(groupedDF, filterByField, sortByField):
    filterDF = groupedDF.get_group(filterByField).dropna(axis=1, how="all")
    filterDF = filterDF.sort_values(sortByField)

    return filterDF


def getClosedLoopDays(groupedData, qualCriteria, metadata):
    # filter by basal data and sort by time
    if "basal" in groupedData.type.unique():
        basalData = filterAndSort(groupedData, "basal", "time")

        # get closed loop days
        nTB = qualCriteria["nTempBasalsPerDayIsClosedLoop"]

        tbDataFrame = basalData.loc[basalData.deliveryType == "temp", ["time"]]
        tbDataFrame.index = pd.to_datetime(tbDataFrame["time"])
        tbDataFrame = tbDataFrame.drop(["time"], axis=1)
        tbDataFrame["basal.temp.count"] = 1
        nTempBasalsPerDay = tbDataFrame.resample("D").sum()
        closedLoopDF = pd.DataFrame(nTempBasalsPerDay,
                                    index=nTempBasalsPerDay.index.date)
        closedLoopDF["date"] = nTempBasalsPerDay.index.date
        closedLoopDF["basal.closedLoopDays"] = \
            closedLoopDF["basal.temp.count"] >= nTB
        nClosedLoopDays = closedLoopDF["basal.closedLoopDays"].sum()

        # get the number of days with 670g
        basalData["date"] = pd.to_datetime(basalData.time).dt.date
        bdGroup = basalData.groupby("date")
        topPump = bdGroup.deviceId.describe()["top"]
        med670g = pd.DataFrame(topPump.str.contains("1780")).rename(columns={"top":"670g"})
        med670g.reset_index(inplace=True)
        n670gDays = med670g["670g"].sum()

    else:
        closedLoopDF = pd.DataFrame(columns=["basal.closedLoopDays", "date"])
        med670g = pd.DataFrame(columns=["670g", "date"])
        nClosedLoopDays = 0
        n670gDays = 0

    metadata["basal.closedLoopDays.count"] = nClosedLoopDays
    metadata["med670gDays.count"] = n670gDays

    return closedLoopDF, med670g, metadata


def removeInvalidCgmValues(df):
    nBefore = len(df)
    # remove values < 38 and > 402 mg/dL
    df = df.query("(value >= 2.109284236597303) and" +
                  "(value <= 22.314006924003046)")
    nRemoved = nBefore - len(df)

    return df, nRemoved


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


def getCalculatorCounts(groupedData, metadata):
    if "wizard" in groupedData.type.unique():
        # filter by calculator data and sort by time
        calculatorData = filterAndSort(groupedData, "wizard", "time")

        # add dayIndex
        calculatorData["dayIndex"] = pd.DatetimeIndex(calculatorData["time"]).date

        # get rid of duplicates
        calculatorData, nDuplicatesRemoved = \
            removeDuplicates(calculatorData, ["time", "bolus"])

        metadata["calculator.duplicatesRemoved.count"] = nDuplicatesRemoved

        # get start and end times
        calculatorBeginDate, calculatorEndDate = getStartAndEndTimes(calculatorData, "dayIndex")
        metadata["calculator.beginDate"] = calculatorBeginDate
        metadata["calculator.endDate"] = calculatorEndDate

        # group by day and get number of calculator boluses
        catDF = calculatorData.groupby(calculatorData["dayIndex"])
        calculatorPerDay = pd.DataFrame()
        calculatorPerDay["calculator.count"] = catDF.bolus.count()
        calculatorPerDay["date"] = calculatorPerDay.index

    else:
        calculatorPerDay = pd.DataFrame(columns=["calculator.count", "date"])

    return calculatorPerDay, metadata


def getListOfDexcomCGMDays(df):
    # search for dexcom cgms
    searchfor = ["Dex", "tan", "IR", "unk"]
    # create dexcom boolean field
    if "deviceId" in df.columns.values:
        totalCgms = len(df.deviceId.notnull())
        df["dexcomCGM"] = df.deviceId.str.contains("|".join(searchfor))
        percentDexcomCGM = df.dexcomCGM.sum() / totalCgms * 100
    return df, percentDexcomCGM


def dexcomCriteria(df):
    # if day is closed loop or non-dexcom set to 0
    isClosedLoop = (df["basal.closedLoopDays"].fillna(False))
    isNonDexcom = ~(df["cgm.dexcomOnly"].fillna(False))
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

    avgBolusCalculations = \
        round(dayStatsDF.loc[dayStatsDF.qualifyingDay == 1,
                             "calculator.count"].mean(), 1)

    df["qualfiyingDays.avgBolusCalculatorCount"] = avgBolusCalculations

    return df


def getQualifyingTier(df, criteriaName, contDayCriteria,
                      avgBolusCalculationsCriteria, percQualDayCriteria,
                      maxGapToContRatioCriteria):

    tempDF = pd.DataFrame(columns=["avgBolusCalculationsPerDay",
                                   "numberContiguousDays",
                                   "percentQualifyingDays",
                                   "maxGapToContiguousRatio",
                                   "tier"])

    for i in range(0, len(df)-(contDayCriteria-1)):

        tempIndex = min(i+contDayCriteria, len(df))

        numberContiguousDays = df["date"].iloc[i:tempIndex].count()
        tempDF.loc[i, "numberContiguousDays"] = numberContiguousDays

        avgBolusCalculationsPerDay = \
            df["calculator.count"].iloc[i:tempIndex].mean()
        tempDF.loc[i, "avgBolusCalculationsPerDay"] = \
            avgBolusCalculationsPerDay

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
                and avgBolusCalculationsPerDay >= avgBolusCalculationsCriteria
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
                              q["avgBolusCalcsPerDay"][j],
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

donorJsonData = os.path.join(donorFolder,
                             phiDateStamp + "-donorJsonData", "")
if not os.path.isdir(donorJsonData):
    sys.exit("{0} is not a directory".format(donorJsonData))

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
    phiUserID = "PHI-" + userID
    jsonFileName = os.path.join(donorJsonData, phiUserID + ".json")
    fileSize = os.stat(jsonFileName).st_size

    if os.path.exists(jsonFileName):
        metadata["fileSize"] = fileSize
        if fileSize > 1000:
            data = td.load.load_json(jsonFileName)

            # attach upload time to each record, for resolving duplicates
            if "upload" in data.type.unique():
                data = addUploadDate(data)

                # filter by only hybridClosedLoop data
                if "hClosedLoop" in qualCriteria["name"]:
                    if "basal" in data.type.unique():
                        data["date"] = pd.to_datetime(data.time).dt.date
                        bd = data[(data.type == "basal") & (data.deliveryType == "temp")]
                        tempBasalCounts = pd.DataFrame(bd.groupby("date").deliveryType.count()).reset_index()
                        tempBasalCounts.rename({"deliveryType": "tempBasalCounts"}, axis=1, inplace=True)
                        data = pd.merge(data, tempBasalCounts, on="date")
                        data = data[data.tempBasalCounts >= qualCriteria["nTempBasalsPerDayIsClosedLoop"]]
                    else:
                        data = pd.DataFrame(columns=list(data))

                # filter by only 670g data
                if "m670g" in qualCriteria["name"]:
                    data = data[data.deviceId.str.contains("1780")]

                # flatten json
                data = td.clean.flatten_json(data)

                if (("cbg" in data.type.unique()) and ("bolus" in data.type.unique())):

                    # get rid of all negative durations
                    data, numberOfNegativeDurations = removeNegativeDurations(data)
                    metadata["all.negativeDurationsRemoved.count"] = numberOfNegativeDurations

                    # group data by type
                    groupedData = data.groupby(by="type")

                    # %% CGM
                    # filter by cgm and sort by time
                    cgmData = filterAndSort(groupedData, "cbg", "time")

                    # get rid of cbg values too low/high (< 38 & > 402 mg/dL)
                    cgmData, numberOfInvalidCgmValues = removeInvalidCgmValues(cgmData)
                    metadata["cgm.invalidValues.count"] = numberOfInvalidCgmValues

                    # get rid of duplicates that have the same ["deviceTime", "value"]
                    cgmData, nDuplicatesRemovedDeviceTime = removeCgmDuplicates(cgmData, "deviceTime")
                    metadata["cgm.nDuplicatesRemovedDeviceTime.count"] = nDuplicatesRemovedDeviceTime

                    # get rid of duplicates that have the same ["time", "value"]
                    cgmData, nDuplicatesRemovedUtcTime = removeCgmDuplicates(cgmData, "time")

                    metadata["cgm.nDuplicatesRemovedUtcTime.count"] = \
                        nDuplicatesRemovedUtcTime

                    # round time to the nearest 5 minutes
                    cgmData = td.clean.round_time(cgmData, timeIntervalMinutes=5, timeField="time",
                                            roundedTimeFieldName="roundedTime", verbose=False)

                    # get rid of duplicates that have the same "roundedTime"
                    cgmData, nDuplicatesRemovedRoundedTime = removeDuplicates(cgmData, "roundedTime")

                    metadata["cgm.nDuplicatesRemovedRoundedTime.count"] = nDuplicatesRemovedRoundedTime

                    # calculate day or date of data
                    cgmData["dayIndex"] = cgmData.roundedTime.dt.date

                    # get start and end times
                    cgmBeginDate, cgmEndDate = getStartAndEndTimes(cgmData, "dayIndex")
                    metadata["cgm.beginDate"] = cgmBeginDate
                    metadata["cgm.endDate"] = cgmEndDate

                    # get a list of dexcom cgms
                    cgmData, percentDexcom = getListOfDexcomCGMDays(cgmData)
                    metadata["cgm.percentDexcomCGM"] = percentDexcom

                    # group by date (day) and get stats
                    catDF = cgmData.groupby(cgmData["dayIndex"])
                    cgmRecordsPerDay = \
                        pd.DataFrame(catDF.value.count()). \
                        rename(columns={"value": "cgm.count"})
                    dayDate = catDF.dayIndex.describe()["top"]
                    dexcomCGM = catDF.dexcomCGM.describe()["top"]
                    nTypesCGM = catDF.dexcomCGM.describe()["unique"]
                    cgmRecordsPerDay["cgm.dexcomOnly"] = \
                        (dexcomCGM & (nTypesCGM == 1))
                    cgmRecordsPerDay["date"] = cgmRecordsPerDay.index

                    # %% BOLUS
                    # filter by bolus and sort by time
                    bolusData = filterAndSort(groupedData, "bolus", "time")

                    # get rid of duplicates
                    bolusData, nDuplicatesRemoved = removeDuplicates(bolusData, ["time", "normal"])
                    metadata["bolus.duplicatesRemoved.count"] = nDuplicatesRemoved

                    # calculate day or date of data
                    bolusData["dayIndex"] = pd.DatetimeIndex(bolusData.time).date

                    # get start and end times
                    bolusBeginDate, bolusEndDate = getStartAndEndTimes(bolusData,
                                                                       "dayIndex")
                    metadata["bolus.beginDate"] = bolusBeginDate
                    metadata["bolus.endDate"] = bolusEndDate

                    # group by date and get bolusRecordsPerDay
                    catDF = bolusData.groupby(bolusData["dayIndex"])
                    bolusRecordsPerDay = \
                        pd.DataFrame(catDF.subType.count()). \
                        rename(columns={"subType": "bolus.count"})

                    bolusRecordsPerDay["date"] = bolusRecordsPerDay.index

                    # %% GET CALCULATOR DATA (AKA WIZARD DATA)
                    calculatorRecordsPerDay, metadata = getCalculatorCounts(groupedData, metadata)

                    # %% GET CLOSED LOOP DAYS WITH TEMP BASAL DATA
                    isClosedLoopDay, is670g, metadata = \
                        getClosedLoopDays(groupedData, qualCriteria, metadata)

                    # %% CONTIGUOUS DATA
                    # calculate the start and end of contiguous data
                    contiguousBeginDate = max(cgmBeginDate, bolusBeginDate)
                    contiguousEndDate = min(cgmEndDate, bolusEndDate)
                    metadata["contiguous.beginDate"] = contiguousBeginDate
                    metadata["contiguous.endDate"] = contiguousEndDate

                    # create a dataframe over the contiguous time series
                    rng = pd.date_range(contiguousBeginDate, contiguousEndDate).date
                    contiguousData = pd.DataFrame(rng, columns=["date"])

                    # merge data
                    contiguousData = pd.merge(contiguousData, bolusRecordsPerDay,
                                              on="date", how="left")
                    contiguousData = pd.merge(contiguousData, cgmRecordsPerDay,
                                              on="date", how="left")
                    contiguousData = pd.merge(contiguousData, calculatorRecordsPerDay,
                                              on="date", how="left")
                    contiguousData = pd.merge(contiguousData, isClosedLoopDay,
                                              on="date", how="left")
                    contiguousData = pd.merge(contiguousData, is670g,
                                              on="date", how="left")

                    # fill in nan's with 0s
                    for dataType in ["bolus", "cgm", "calculator", "basal.temp"]:
                        contiguousData[dataType + ".count"] = \
                            contiguousData[dataType + ".count"].fillna(0)

                    if ((len(contiguousData) > 0) &
                       (sum(contiguousData["cgm.count"] > 0) > 0) &
                       (sum(contiguousData["bolus.count"] > 0) > 0)):

                        # create an output folder
                        userQualifyFolder = os.path.join(donorQualifyFolder, userID)
                        if not os.path.exists(userQualifyFolder):
                            os.makedirs(userQualifyFolder)

                        # %% QUALIFICATION AT DAY LEVEL
                        # dexcom specific qualification criteria
                        if qualCriteria["name"] == "dexcom":
                            contiguousData = dexcomCriteria(contiguousData)

                        # determine if each day qualifies
                        contiguousData = \
                            isQualifyingDay(contiguousData,
                                            qualCriteria["bolusesPerDay"],
                                            qualCriteria["cgmPercentPerDay"],
                                            criteriaMaxCgmPointsPerDay)
                        # calcuate summary stats
                        metadata = getSummaryStats(metadata, contiguousData)

                        # %% QUALIFICATION OF DATASET
                        contiguousData, metadata = qualify(contiguousData, metadata,
                                                           qualCriteria, dIndex)

                        # %% SAVE RESULTS
                        contiguousData.index.name = "dayIndex"
                        dSFileName = os.path.join(
                            userQualifyFolder, userID + "-qualified-as-" +
                            metadata[qualCriteria["tierAbbr"] + ".topTier"].values[0] +
                            "-on-" + qualifiedOn + "-for-" + qualCriteria["name"] +
                            "-dayStats.csv")

                        contiguousData.to_csv(dSFileName)

                        # append meta data to the user results
                        allMetaData = pd.concat([allMetaData, metadata], axis=0, sort=False)

                        # update on progress
                        print(round((dIndex - startIndex + 1) /
                                    (endIndex - startIndex) * 100, 1),
                              "% ", dIndex, "of", endIndex - 1, "qualifed as:",
                              metadata[qualCriteria["tierAbbr"] +
                                       ".topTier"].values)

allMetaData.index.name = "dIndex"
uniqueDonors = pd.concat([uniqueDonors, allMetaData], axis=1)
aMFileName = os.path.join(donorFolder,
                          phiDateStamp + "-records-" + str(startIndex) + "-" +
                          str(endIndex - 1) + "-qualified-on-" + qualifiedOn +
                          "-for-" + qualCriteria["name"] + "-metadata.csv")

uniqueDonors.to_csv(aMFileName)
