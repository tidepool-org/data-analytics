#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qualify donor data
"""


# %% REQUIRED LIBRARIES
import os
import argparse
import json
import ast
import pandas as pd
import datetime as dt
import numpy as np


# %% USER INPUTS (choices to be made in order to run the code)
codeDescription = "qualify donor data"
parser = argparse.ArgumentParser(description=codeDescription)

parser.add_argument(
    "-d",
    "--date-stamp",
    dest="date_stamp",
    default=dt.datetime.now().strftime("%Y-%m-%d"),
    help="date, in '%Y-%m-%d' format, of the date when " +
    "donors were accepted"
)

parser.add_argument(
    "-u",
    "--userid",
    dest="userid",
    default=np.nan,
    help="userid of account shared with the donor group or master account"
)

parser.add_argument(
    "-o",
    "--output-data-path",
    dest="data_path",
    default=os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "data"
        )
    ),
    help="the output path where the data is stored"
)

parser.add_argument("-q",
                    "--qualification-criteria",
                    dest="qualificationCriteria",
                    default=os.path.abspath(
                        os.path.join(
                        os.path.dirname(__file__),
                        "tidepool-qualification-criteria.json")
                    ),
                    type=argparse.FileType('r'),
                    help="JSON file to be processed, see " +
                         "tidepool-qualification-critier.json " +
                         "for a list of required fields")

parser.add_argument(
    "-s",
    "--save-dayStats",
    dest="save_dayStats",
    default="False",
    help="save the day stats used for qualifying (True/False)"
)

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


def removeNegativeDurations(df):
    if "duration" in list(df):

        nNegativeDurations = sum(df.duration.astype(float) < 0)
        if nNegativeDurations > 0:
            df = df[~(df.duration.astype(float) < 0)]
    else:
        nNegativeDurations = np.nan

    return df, nNegativeDurations


def add_uploadDateTime(df):
    if "upload" in data.type.unique():
        uploadTimes = pd.DataFrame(
            df[df.type == "upload"].groupby("uploadId").time.describe()["top"]
        )
    else:
        uploadTimes = pd.DataFrame(columns=["top"])
    # if an upload does not have an upload date, then add one
    # NOTE: this is a new fix introduced with healthkit data...we now have
    # data that does not have an upload record
    unique_uploadIds = set(df["uploadId"].unique())
    unique_uploadRecords = set(
        df.loc[df["type"] == "upload", "uploadId"].unique()
    )
    uploadIds_missing_uploadRecords = unique_uploadIds - unique_uploadRecords

    for upId in uploadIds_missing_uploadRecords:
        last_upload_time = df.loc[df["uploadId"] == upId, "time"].max()
        uploadTimes.loc[upId, "top"] = last_upload_time

    uploadTimes.reset_index(inplace=True)
    uploadTimes.rename(
        columns={
            "top": "uploadTime",
            "index": "uploadId"
        },
        inplace=True
    )
    df = pd.merge(df, uploadTimes, how='left', on='uploadId')
    df["uploadTime"] = pd.to_datetime(df["uploadTime"])

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
    else:
        df["dexcomCGM"] = False
        percentDexcomCGM = 0
        print("no deviceId associated with cgm data")
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


def temp_remove_fields(df, removeFields):

    tempRemoveFields = list(set(df) & set(removeFields))
    tempDf = df[tempRemoveFields]
    df = df.drop(columns=tempRemoveFields)

    return df, tempDf


def flatten_json(df, doNotFlattenList):
    # remove fields that we don't want to flatten
    df, holdData = temp_remove_fields(df, doNotFlattenList)

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
    t = pd.to_datetime(df[timeField].astype('datetime64[ns]'))

    # calculate the time between consecutive records
    t_shift = pd.to_datetime(df[timeField].astype('datetime64[ns]').shift(1))
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


def make_folder_if_doesnt_exist(folder_paths):
    ''' function requires a single path or a list of paths'''
    if not isinstance(folder_paths, list):
        folder_paths = [folder_paths]
    for folder_path in folder_paths:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
    return


# %% load in all data for user
userid = args.userid
if pd.isnull(userid):
    userid = input("Enter Tidepool userid:\n")

metadata = pd.DataFrame(index=[userid])

phi_date_stamp = "PHI-" + args.date_stamp
donor_folder = os.path.join(args.data_path, phi_date_stamp + "-donor-data")

qualCriteria = json.load(args.qualificationCriteria)
criteriaMaxCgmPointsPerDay = 1440 / qualCriteria["timeFreqMin"]
qualifiedOn = dt.datetime.now().strftime("%Y-%m-%d")

qualify_path = os.path.join(
    donor_folder,
    args.date_stamp + "-qualified-by-" + qualCriteria["name"] + "-criteria"
)

metadata_path = os.path.join(qualify_path, "metadata")
dayStats_path = os.path.join(qualify_path, "dayStats")
make_folder_if_doesnt_exist([metadata_path, dayStats_path])

dataset_path = os.path.join(donor_folder, phi_date_stamp + "-csvData")
file_path = os.path.join(dataset_path, "PHI-" + userid + ".csv")

if os.path.exists(file_path):
    file_size = os.stat(file_path).st_size
    metadata["fileSize"] = file_size
    if file_size > 1000:
        data = pd.read_csv(file_path, low_memory=False)

        # attach upload time to each record, for resolving duplicates
        data = add_uploadDateTime(data)

        # remove extra data types that are not needed for qualification
        data = data[
            (data["type"] == "cbg") |
            (data["type"] == "basal") |
            (data["type"] == "bolus") |
            (data["type"] == "wizard")
        ]

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
        do_not_flatten_list = ["suppressed", "recommended", "payload"]
        data = flatten_json(data, do_not_flatten_list)

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
            cgmData = round_time(
                cgmData,
                timeIntervalMinutes=5,
                timeField="time",
                roundedTimeFieldName="roundedTime",
                verbose=False
            )

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

            # % GET CALCULATOR DATA (AKA WIZARD DATA)
            calculatorRecordsPerDay, metadata = getCalculatorCounts(groupedData, metadata)

            # % GET CLOSED LOOP DAYS WITH TEMP BASAL DATA
            isClosedLoopDay, is670g, metadata = \
                getClosedLoopDays(groupedData, qualCriteria, metadata)

            # % CONTIGUOUS DATA
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
                dataType = dataType + ".count"

                if dataType in list(contiguousData):
                    contiguousData[dataType] = \
                        contiguousData[dataType].fillna(0)

            if ((len(contiguousData) > 0) &
               (sum(contiguousData["cgm.count"] > 0) > 0) &
               (sum(contiguousData["bolus.count"] > 0) > 0)):

                # % QUALIFICATION AT DAY LEVEL
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

                # % QUALIFICATION OF DATASET
                contiguousData, metadata = qualify(contiguousData, metadata,
                                                   qualCriteria, userid)

                # % SAVE RESULTS
                tier = metadata[qualCriteria["tierAbbr"] + ".topTier"].values[0]
                contiguousData.index.name = "dayIndex"
                if ast.literal_eval(args.save_dayStats):
                    contiguousData.to_csv(
                        os.path.join(dayStats_path, userid + ".csv")
                    )

                # update on progress
                output_message = "qualifed as %s" % tier
                print(userid, output_message)
        else:
            output_message = "file does not contain cgm and bolus data"
            print(userid, output_message)
    else:
        output_message = "file does not contain enough data"
        print(userid, output_message)
else:
    output_message = "file does not exist"
    print(userid, output_message)
metadata["outputMessage"] = output_message
metadata.to_csv(
    os.path.join(metadata_path, userid + ".csv")
)
