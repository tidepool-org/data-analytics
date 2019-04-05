#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Description: Function library file for Tidepool rolling statistics analysis
Created: 2019-02-06
Author: Ed Nykaza & Jason Meno
License: BSD-2-Clause
"""

import pandas as pd
import datetime as dt
import numpy as np
import os
import sys
import requests
import json
import getpass
from pytz import timezone
from datetime import timedelta


# %% Define Functions
def get_data_from_api(
    email=np.nan,
    password=np.nan,
    years_of_data=10,
    userid_of_shared_user=np.nan,
):

    if pd.isnull(email):
        email = input("Enter Tidepool email address:\n")

    if pd.isnull(password):
        password = getpass.getpass("Enter password:\n")

    df = pd.DataFrame()
    url1 = "https://api.tidepool.org/auth/login"
    url3 = "https://api.tidepool.org/auth/logout"

    myResponse = requests.post(url1, auth=(email, password))

    if(myResponse.ok):
        xtoken = myResponse.headers["x-tidepool-session-token"]

        if pd.isnull(userid_of_shared_user):
            userid = json.loads(myResponse.content.decode())["userid"]
        else:
            userid = userid_of_shared_user

        endDate = pd.datetime.now()
        
        print("Fetching Data From Previous Years... ", end="")
        for years in range(1, years_of_data + 1):
            print(years, " ", end="")
            startDate = endDate - pd.Timedelta(365, unit="d")
            
            url2 = "https://api.tidepool.org/data/" + userid + \
                "?endDate=" + endDate.strftime("%Y-%m-%d") + \
                "T23:59:59.000Z&startDate=" + \
                startDate.strftime("%Y-%m-%d") + "T00:00:00.000Z"

            headers = {
                "x-tidepool-session-token": xtoken,
                "Content-Type": "application/json"
                }

            myResponse2 = requests.get(url2, headers=headers)
            if(myResponse2.ok):

                usersData = json.loads(myResponse2.content.decode())
                tempDF = pd.DataFrame(usersData)
                df = pd.concat([df, tempDF], ignore_index=True, sort=False)

            else:
                print("ERROR in year ", years, myResponse2.status_code)

            endDate = startDate - pd.Timedelta(1, unit="d")
    else:
        print("ERROR in getting token ", myResponse.status_code)
        myResponse2 = np.nan

    myResponse3 = requests.post(url3, auth=(email, password))

    responses = [myResponse, myResponse2, myResponse3]
    print("")
    return df, responses, userid


# Old api fetch function (saved for comparison)
def get_user_data(email, password, userid):

    url1 = "https://api.tidepool.org/auth/login"
    myResponse = requests.post(url1, auth=(email, password))
    usersData = 0

    if(myResponse.ok):
        xtoken = myResponse.headers["x-tidepool-session-token"]
        url2 = "https://api.tidepool.org/data/" + userid
        headers = {
            "x-tidepool-session-token": xtoken,
            "Content-Type": "application/json"
            }

        myResponse2 = requests.get(url2, headers=headers)
        if(myResponse2.ok):

            usersData = json.loads(myResponse2.content.decode())
            usersData = pd.DataFrame(usersData)

        else:
            print("ERROR", myResponse2.status_code)
    else:
        print("ERROR", myResponse.status_code)

    return usersData

def convertDeprecatedTimezoneToAlias(df, tzAlias):
    if "timezone" in df:
        uniqueTimezones = df.timezone.unique()
        uniqueTimezones = uniqueTimezones[pd.notnull(df.timezone.unique())]

        for uniqueTimezone in uniqueTimezones:
            alias = tzAlias.loc[tzAlias.tz.str.endswith(uniqueTimezone),
                                ["alias"]].values
            if len(alias) == 1:
                df.loc[df.timezone == uniqueTimezone, ["timezone"]] = alias

    return df


def largeTimezoneOffsetCorrection(df):

    while ((df.timezoneOffset > 840).sum() > 0):
        df.loc[df.timezoneOffset > 840, ["conversionOffset"]] = \
            df.loc[df.timezoneOffset > 840, ["conversionOffset"]] - \
            (1440 * 60 * 1000)

        df.loc[df.timezoneOffset > 840, ["timezoneOffset"]] = \
            df.loc[df.timezoneOffset > 840, ["timezoneOffset"]] - 1440

    while ((df.timezoneOffset < -720).sum() > 0):
        df.loc[df.timezoneOffset < -720, ["conversionOffset"]] = \
            df.loc[df.timezoneOffset < -720, ["conversionOffset"]] + \
            (1440 * 60 * 1000)

        df.loc[df.timezoneOffset < -720, ["timezoneOffset"]] = \
            df.loc[df.timezoneOffset < -720, ["timezoneOffset"]] + 1440

    return df


def createContiguousDaySeries(df):
    firstDay = df.date.min()
    lastDay = df.date.max()
    rng = pd.date_range(firstDay, lastDay).date
    contiguousDaySeries = \
        pd.DataFrame(rng, columns=["date"]).sort_values(
                "date", ascending=False).reset_index(drop=True)

    return contiguousDaySeries


def getAndPreprocessUploadRecords(df):
    # first make sure deviceTag is in string format
    df["deviceTags"] = df.deviceTags.astype(str)
    # filter by type upload
    ud = df[df.type == "upload"].copy()
    # define a device type (e.g., pump, cgm, or healthkit)
    ud["deviceType"] = np.nan
    ud.loc[ud.deviceTags.str.contains("pump"), ["deviceType"]] = "pump"

    # this is for non-healthkit cgm records only
    ud.loc[((ud.deviceTags.str.contains("cgm")) &
            (ud.timeProcessing != "none")), ["deviceType"]] = "cgm"

    ud.loc[((ud.deviceTags.str.contains("cgm")) &
            (ud.timeProcessing == "none")), ["deviceType"]] = "healthkit"

    return ud


def getAndPreprocessNonDexApiCgmRecords(df):
    # non-healthkit cgm and exclude dexcom-api data
    if "payload" in df:
        # convert payloads to strings
        df["isDexcomAPI"] = df.payload.astype(str).str.contains("systemTime")
        cd = df[(df.type == "cbg") &
                (df.timezoneOffset.notnull()) &
                (~df.isDexcomAPI.fillna(False))].copy()

    else:
        cd = df[(df.type == "cbg") & (df.timezoneOffset.notnull())]

    return cd


def getTimezoneOffset(currentDate, currentTimezone):

    tz = timezone(currentTimezone)
    # here we add 1 day to the current date to account for changes to/from DST
    tzoNum = int(tz.localize(currentDate + timedelta(days=1)).strftime("%z"))
    tzoHours = np.floor(tzoNum / 100)
    tzoMinutes = round((tzoNum / 100 - tzoHours) * 100, 0)
    tzoSign = np.sign(tzoHours)
    tzo = int((tzoHours * 60) + (tzoMinutes * tzoSign))

    return tzo


def getTzoForDateTime(currentDateTime, currentTimezone):

    tz = timezone(currentTimezone)
    tzoNum = int(tz.localize(pd.to_datetime(currentDateTime)).strftime("%z"))
    tzoHours = np.floor(tzoNum / 100)
    tzoMinutes = round((tzoNum / 100 - tzoHours) * 100, 0)
    tzoSign = np.sign(tzoHours)
    tzo = int((tzoHours * 60) + (tzoMinutes * tzoSign))

    return tzo


def isDSTChangeDay(currentDate, currentTimezone):
    tzoCurrentDay = getTimezoneOffset(pd.to_datetime(currentDate),
                                      currentTimezone)
    tzoPreviousDay = getTimezoneOffset(pd.to_datetime(currentDate) +
                                       timedelta(days=-1), currentTimezone)

    return (tzoCurrentDay != tzoPreviousDay)


def addAnnotation(df, idx, annotationMessage):
    if pd.notnull(df.loc[idx, "est.annotations"]):
        df.loc[idx, ["est.annotations"]] = df.loc[idx, "est.annotations"] + \
            ", " + annotationMessage
    else:
        df.loc[idx, ["est.annotations"]] = annotationMessage

    return df


def addDeviceDaySeries(df, dfContDays, deviceTypeName):
    if len(df) > 0:
        dfDayGroups = df.groupby("date")
        dfDaySeries = pd.DataFrame(dfDayGroups.timezoneOffset.median())
        if "upload" in deviceTypeName:
            if "timezone" in df:
                if dfDayGroups.timezone.count().values[0] > 0:
                    dfDaySeries["timezone"] = \
                        dfDayGroups.timezone.describe()["top"]
                    # get the timezone offset for the timezone
                    for i in dfDaySeries.index:
                        if pd.notnull(dfDaySeries.loc[i, "timezone"]):
                            tzo = getTimezoneOffset(
                                    pd.to_datetime(i),
                                    dfDaySeries.loc[i, "timezone"])
                            dfDaySeries.loc[i, ["timezoneOffset"]] = tzo

                    dfDaySeries["timeProcessing"] = \
                        dfDayGroups.timeProcessing.describe()["top"]

        dfDaySeries = dfDaySeries.add_prefix(deviceTypeName + "."). \
            rename(columns={deviceTypeName + ".date": "date"})

        dfContDays = pd.merge(dfContDays, dfDaySeries.reset_index(),
                              on="date", how="left")

    else:
        dfContDays[deviceTypeName + ".timezoneOffset"] = np.nan

    return dfContDays


def imputeUploadRecords(df, contDays, deviceTypeName):
    daySeries = \
        addDeviceDaySeries(df, contDays, deviceTypeName)

    if ((len(df) > 0) & (deviceTypeName + ".timezone" in daySeries)):
        for i in daySeries.index[1:]:
            if pd.isnull(daySeries[deviceTypeName + ".timezone"][i]):
                    daySeries.loc[i, [deviceTypeName + ".timezone"]] = \
                        daySeries.loc[i-1, deviceTypeName + ".timezone"]
            if pd.notnull(daySeries[deviceTypeName + ".timezone"][i]):
                tz = daySeries.loc[i, deviceTypeName + ".timezone"]
                tzo = \
                    getTimezoneOffset(pd.to_datetime(daySeries.loc[i, "date"]),
                                      tz)
                daySeries.loc[i, deviceTypeName + ".timezoneOffset"] = tzo

            if pd.notnull(daySeries[deviceTypeName + ".timeProcessing"][i-1]):
                daySeries.loc[i, deviceTypeName + ".timeProcessing"] = \
                    daySeries.loc[i-1, deviceTypeName + ".timeProcessing"]

    else:
        daySeries[deviceTypeName + ".timezone"] = np.nan
        daySeries[deviceTypeName + ".timeProcessing"] = np.nan

    return daySeries


def estimateTzAndTzoWithUploadRecords(cDF):

    cDF["est.type"] = np.nan
    cDF["est.gapSize"] = np.nan
    cDF["est.timezoneOffset"] = cDF["upload.timezoneOffset"]
    cDF["est.annotations"] = np.nan

    if "upload.timezone" in cDF:
        cDF.loc[cDF["upload.timezone"].notnull(), ["est.type"]] = "UPLOAD"
        cDF["est.timezone"] = cDF["upload.timezone"]
        cDF["est.timeProcessing"] = cDF["upload.timeProcessing"]
    else:
        cDF["est.timezone"] = np.nan
        cDF["est.timeProcessing"] = np.nan

    cDF.loc[((cDF["est.timezoneOffset"] !=
              cDF["home.imputed.timezoneOffset"]) &
            (pd.notnull(cDF["est.timezoneOffset"]))),
            "est.annotations"] = "travel"

    return cDF


def estimateTzAndTzoWithDeviceRecords(cDF):

    # 2A. use the TZO of the pump or cgm device if it exists on a given day. In
    # addition, compare the TZO to one of the imputed day series (i.e., the
    # upload and home series to see if the TZ can be inferred)
    for deviceType in ["pump", "cgm"]:
        # find the indices of days where a TZO estimate has not been made AND
        # where the device (e.g., pump or cgm) TZO has data
        sIndices = cDF[((cDF["est.timezoneOffset"].isnull()) &
                        (cDF[deviceType + ".timezoneOffset"].notnull()))].index
        # compare the device TZO to the imputed series to infer time zone
        cDF = compareDeviceTzoToImputedSeries(cDF, sIndices, deviceType)

    # 2B. if the TZ cannot be inferred with 2A, then see if the TZ can be
    # inferred from the previous day's TZO. If the device TZO is equal to the
    # previous day's TZO, AND if the previous day has a TZ estimate, use the
    # previous day's TZ estimate for the current day's TZ estimate
    for deviceType in ["pump", "cgm"]:
        sIndices = cDF[((cDF["est.timezoneOffset"].isnull()) &
                        (cDF[deviceType + ".timezoneOffset"].notnull()))].index

        cDF = compareDeviceTzoToPrevDayTzo(cDF, sIndices, deviceType)

    # 2C. after 2A and 2B, check the DEVICE estimates to make sure that the
    # pump and cgm tzo do not differ by more than 60 minutes. If they differ
    # by more that 60 minutes, then mark the estimate as UNCERTAIN. Also, we
    # allow the estimates to be off by 60 minutes as there are a lot of cases
    # where the devices are off because the user changes the time for DST,
    # at different times
    # Apply a lambda comparison on columns that might be all null
    sIndices = cDF[((cDF["est.type"].apply(lambda x: x == "DEVICE")) &
                    (cDF["pump.timezoneOffset"].notnull()) &
                    (cDF["cgm.timezoneOffset"].notnull()) &
                    (cDF["pump.timezoneOffset"] != cDF["cgm.timezoneOffset"])
                    )].index

    tzoDiffGT60 = abs(cDF.loc[sIndices, "cgm.timezoneOffset"] -
                      cDF.loc[sIndices, "pump.timezoneOffset"]) > 60

    idx = tzoDiffGT60.index[tzoDiffGT60]

    cDF.loc[idx, ["est.type"]] = "UNCERTAIN"
    for i in idx:
        cDF = addAnnotation(cDF, i, "pump-cgm-tzo-mismatch")

    return cDF


def addHomeTimezone(df, contDays):

    if "timezone" in df:
        homeTimezone = df["timezone"].describe()["top"]
        tzo = contDays.date.apply(
                lambda x: getTimezoneOffset(pd.to_datetime(x), homeTimezone))

        contDays["home.imputed.timezoneOffset"] = tzo
        contDays["home.imputed.timezone"] = homeTimezone

    else:
        contDays["home.imputed.timezoneOffset"] = np.nan
        contDays["home.imputed.timezone"] = np.nan
    contDays["home.imputed.timeProcessing"] = np.nan

    return contDays


def getRangeOfTZOsForTimezone(tz):
    minMaxTzo = [getTimezoneOffset(pd.to_datetime("1/1/2017"), tz),
                 getTimezoneOffset(pd.to_datetime("5/1/2017"), tz)]

    rangeOfTzo = np.arange(int(min(minMaxTzo)), int(max(minMaxTzo))+1, 15)

    return rangeOfTzo


def tzoRangeWithComparisonTz(df, i, comparisonTz):
    # if we have a previous timezone estimate, then calcuate the range of
    # timezone offset values for that time zone
    if pd.notnull(comparisonTz):
        rangeTzos = getRangeOfTZOsForTimezone(comparisonTz)
    else:
        comparisonTz = np.nan
        rangeTzos = np.array([])

    return rangeTzos


def tzAndTzoRangePreviousDay(df, i):
    # if we have a previous timezone estimate, then calcuate the range of
    # timezone offset values for that time zone
    comparisonTz = df.loc[i-1, "est.timezone"]

    rangeTzos = tzoRangeWithComparisonTz(df, i, comparisonTz)

    return comparisonTz, rangeTzos


def tzAndTzoRangeWithHomeTz(df, i):
    # if we have a previous timezone estimate, then calcuate the range of
    # timezone offset values for that time zone
    comparisonTz = df.loc[i, "home.imputed.timezone"]

    rangeTzos = tzoRangeWithComparisonTz(df, i, comparisonTz)

    return comparisonTz, rangeTzos


def assignTzoFromImputedSeries(df, i, imputedSeries):
    df.loc[i, ["est.type"]] = "DEVICE"

    df.loc[i, ["est.timezoneOffset"]] = \
        df.loc[i, imputedSeries + ".timezoneOffset"]

    df.loc[i, ["est.timezone"]] = \
        df.loc[i, imputedSeries + ".timezone"]

    df.loc[i, ["est.timeProcessing"]] = \
        df.loc[i, imputedSeries + ".timeProcessing"]

    return df


def compareDeviceTzoToImputedSeries(df, sIdx, device):
    for i in sIdx:
        # if the device tzo = imputed tzo, then chose the imputed tz and tzo
        # note, dst is accounted for in the imputed tzo
        for imputedSeries in ["pump.upload.imputed", "cgm.upload.imputed",
                              "healthkit.upload.imputed", "home.imputed"]:
            # if the estimate has not already been made
            if pd.isnull(df.loc[i, "est.timezone"]):

                if df.loc[i, device + ".timezoneOffset"] == \
                  df.loc[i, imputedSeries + ".timezoneOffset"]:

                    assignTzoFromImputedSeries(df, i, imputedSeries)

                    df = addAnnotation(df, i,
                                       "tz-inferred-from-" + imputedSeries)

                # if the imputed series has a timezone estimate, then see if
                # the current day is a dst change day
                elif (pd.notnull(df.loc[i, imputedSeries + ".timezone"])):
                    imputedTimezone = df.loc[i, imputedSeries + ".timezone"]
                    if isDSTChangeDay(df.loc[i, "date"], imputedTimezone):

                        dstRange = getRangeOfTZOsForTimezone(imputedTimezone)
                        if ((df.loc[i, device + ".timezoneOffset"] in dstRange)
                          & (df.loc[i, imputedSeries + ".timezoneOffset"] in dstRange)):

                            assignTzoFromImputedSeries(df, i, imputedSeries)

                            df = addAnnotation(df, i, "dst-change-day")
                            df = addAnnotation(
                                    df, i, "tz-inferred-from-" + imputedSeries)

    return df


def assignTzoFromPreviousDay(df, i, previousDayTz):

    df.loc[i, ["est.type"]] = "DEVICE"
    df.loc[i, ["est.timezone"]] = previousDayTz
    df.loc[i, ["est.timezoneOffset"]] = \
        getTimezoneOffset(pd.to_datetime(df.loc[i, "date"]), previousDayTz)

    df.loc[i, ["est.timeProcessing"]] = df.loc[i-1, "est.timeProcessing"]
    df = addAnnotation(df, i, "tz-inferred-from-prev-day")

    return df


def assignTzoFromDeviceTzo(df, i, device):

    df.loc[i, ["est.type"]] = "DEVICE"
    df.loc[i, ["est.timezoneOffset"]] = \
        df.loc[i, device + ".timezoneOffset"]
    df.loc[i, ["est.timeProcessing"]] = \
        df.loc[i, device + ".upload.imputed.timeProcessing"]

    df = addAnnotation(df, i, "likely-travel")
    df = addAnnotation(df, i, "tzo-from-" + device)

    return df


def compareDeviceTzoToPrevDayTzo(df, sIdx, device):

    for i in sIdx[sIdx > 0]:

        # first see if the previous record has a tzo
        if (pd.notnull(df.loc[i-1, "est.timezoneOffset"])):

            previousDayTz, dstRange = tzAndTzoRangePreviousDay(df, i)
            timeDiff = abs((df.loc[i, device + ".timezoneOffset"]) -
                           df.loc[i-1, "est.timezoneOffset"])

            # next see if the previous record has a tz
            if (pd.notnull(df.loc[i-1, "est.timezone"])):

                if timeDiff == 0:
                    assignTzoFromPreviousDay(df, i, previousDayTz)

                # see if the previous day's tzo and device tzo are within the
                # dst range (as that is a common problem with this data)
                elif ((df.loc[i, device + ".timezoneOffset"] in dstRange)
                      & (df.loc[i-1, "est.timezoneOffset"] in dstRange)):

                    # then see if it is DST change day
                    if isDSTChangeDay(df.loc[i, "date"], previousDayTz):

                        df = addAnnotation(df, i, "dst-change-day")
                        assignTzoFromPreviousDay(df, i, previousDayTz)

                    # if it is not DST change day, then mark this as uncertain
                    else:
                        # also, check to see if the difference between device.
                        # tzo and prev.tzo is less than the expected dst
                        # difference. There is a known issue where the BtUTC
                        # procedure puts clock drift into the device.tzo,
                        # and as a result the tzo can be off by 15, 30,
                        # or 45 minutes.
                        if (((df.loc[i, device + ".timezoneOffset"] ==
                              min(dstRange)) |
                            (df.loc[i, device + ".timezoneOffset"] ==
                             max(dstRange))) &
                           ((df.loc[i-1, "est.timezoneOffset"] ==
                             min(dstRange)) |
                            (df.loc[i-1, "est.timezoneOffset"] ==
                             max(dstRange)))):

                            df.loc[i, ["est.type"]] = "UNCERTAIN"
                            df = addAnnotation(df, i,
                                               "likely-dst-error-OR-travel")

                        else:

                            df.loc[i, ["est.type"]] = "UNCERTAIN"
                            df = addAnnotation(df, i,
                                               "likely-15-min-dst-error")

                # next see if time difference between device.tzo and prev.tzo
                # is off by 720 minutes, which is indicative of a common
                # user AM/PM error
                elif timeDiff == 720:
                    df.loc[i, ["est.type"]] = "UNCERTAIN"
                    df = addAnnotation(df, i, "likely-AM-PM-error")

                # if it doesn't fall into any of these cases, then the
                # tzo difference is likely due to travel
                else:
                    df = assignTzoFromDeviceTzo(df, i, device)

            elif timeDiff == 0:
                df = assignTzoFromDeviceTzo(df, i, device)

        # if there is no previous record to compare with check for dst errors,
        # and if there are no errors, it is likely a travel day
        else:

            comparisonTz, dstRange = tzAndTzoRangeWithHomeTz(df, i)
            timeDiff = abs((df.loc[i, device + ".timezoneOffset"]) -
                           df.loc[i, "home.imputed.timezoneOffset"])

            if ((df.loc[i, device + ".timezoneOffset"] in dstRange)
               & (df.loc[i, "home.imputed.timezoneOffset"] in dstRange)):

                # see if it is DST change day
                if isDSTChangeDay(df.loc[i, "date"], comparisonTz):

                    df = addAnnotation(df, i, "dst-change-day")
                    df.loc[i, ["est.type"]] = "DEVICE"
                    df.loc[i, ["est.timezoneOffset"]] = \
                        df.loc[i, device + ".timezoneOffset"]
                    df.loc[i, ["est.timezone"]] = \
                        df.loc[i, "home.imputed.timezone"]
                    df.loc[i, ["est.timeProcessing"]] = \
                        df.loc[i, device + ".upload.imputed.timeProcessing"]

                # if it is not DST change day, then mark this as uncertain
                else:
                    # also, check to see if the difference between device.
                    # tzo and prev.tzo is less than the expected dst
                    # difference. There is a known issue where the BtUTC
                    # procedure puts clock drift into the device.tzo,
                    # and as a result the tzo can be off by 15, 30,
                    # or 45 minutes.
                    if (((df.loc[i, device + ".timezoneOffset"] ==
                          min(dstRange)) |
                        (df.loc[i, device + ".timezoneOffset"] ==
                         max(dstRange))) &
                       ((df.loc[i, "home.imputed.timezoneOffset"] ==
                         min(dstRange)) |
                        (df.loc[i, "home.imputed.timezoneOffset"] ==
                         max(dstRange)))):

                        df.loc[i, ["est.type"]] = "UNCERTAIN"
                        df = addAnnotation(df, i, "likely-dst-error-OR-travel")

                    else:

                        df.loc[i, ["est.type"]] = "UNCERTAIN"
                        df = addAnnotation(df, i, "likely-15-min-dst-error")

            # next see if time difference between device.tzo and prev.tzo
            # is off by 720 minutes, which is indicative of a common
            # user AM/PM error
            elif timeDiff == 720:
                df.loc[i, ["est.type"]] = "UNCERTAIN"
                df = addAnnotation(df, i, "likely-AM-PM-error")

            # if it doesn't fall into any of these cases, then the
            # tzo difference is likely due to travel

            else:
                df = assignTzoFromDeviceTzo(df, i, device)

    return df


def getImputIndices(df, sIdx, hIdx):

    lastDayIdx = len(df) - 1

    currentDayIdx = sIdx.min()
    tempList = pd.Series(hIdx) - currentDayIdx
    prevDayIdx = currentDayIdx - 1
    nextDayIdx = \
        min(currentDayIdx + min(tempList[tempList >= 0]), lastDayIdx)

    return currentDayIdx, prevDayIdx, nextDayIdx


def imputeByTimezone(df, currentDay, prevDaywData, nextDaywData):

    gapSize = (nextDaywData - currentDay)

    if prevDaywData >= 0:

        if df.loc[prevDaywData, "est.timezone"] == \
          df.loc[nextDaywData, "est.timezone"]:

            tz = df.loc[prevDaywData, "est.timezone"]

            for i in range(currentDay, nextDaywData):

                df.loc[i, ["est.timezone"]] = tz

                df.loc[i, ["est.timezoneOffset"]] = \
                    getTimezoneOffset(pd.to_datetime(df.loc[i, "date"]), tz)

                df.loc[i, ["est.type"]] = "IMPUTE"

                df = addAnnotation(df, i, "gap=" + str(gapSize))
                df.loc[i, ["est.gapSize"]] = gapSize

        # TODO: this logic should be updated to handle the edge case
        # where the day before and after the gap have differing TZ, but
        # the same TZO. In that case the gap should be marked as UNCERTAIN
        elif df.loc[prevDaywData, "est.timezoneOffset"] == \
          df.loc[nextDaywData, "est.timezoneOffset"]:

            for i in range(currentDay, nextDaywData):

                df.loc[i, ["est.timezoneOffset"]] = \
                    df.loc[prevDaywData, "est.timezoneOffset"]

                df.loc[i, ["est.type"]] = "IMPUTE"

                df = addAnnotation(df, i, "gap=" + str(gapSize))
                df.loc[i, ["est.gapSize"]] = gapSize

        else:
            for i in range(currentDay, nextDaywData):
                df.loc[i, ["est.type"]] = "UNCERTAIN"
                df = addAnnotation(df, i, "unable-to-impute-tzo")

    else:
        for i in range(currentDay, nextDaywData):
            df.loc[i, ["est.type"]] = "UNCERTAIN"
            df = addAnnotation(df, i, "unable-to-impute-tzo")

    return df


def imputeTzAndTzo(cDF):

    sIndices = cDF[cDF["est.timezoneOffset"].isnull()].index
    hasTzoIndices = cDF[cDF["est.timezoneOffset"].notnull()].index
    if len(hasTzoIndices) > 0:
        if len(sIndices) > 0:
            lastDay = max(sIndices)

            while ((sIndices.min() < max(hasTzoIndices)) &
                   (len(sIndices) > 0)):

                currentDay, prevDayWithDay, nextDayIdx = \
                    getImputIndices(cDF, sIndices, hasTzoIndices)

                cDF = imputeByTimezone(cDF, currentDay,
                                       prevDayWithDay, nextDayIdx)

                sIndices = cDF[((cDF["est.timezoneOffset"].isnull()) &
                                (~cDF["est.annotations"].str.contains(
                                "unable-to-impute-tzo").fillna(False)))].index

                hasTzoIndices = cDF[cDF["est.timezoneOffset"].notnull()].index

            # try to impute to the last day (earliest day) in the dataset
            # if the last record has a timezone that is the home record, then
            # impute using the home timezone
            if len(sIndices) > 0:
                currentDay = min(sIndices)
                prevDayWithDay = currentDay - 1
                gapSize = lastDay - currentDay

                for i in range(currentDay, lastDay + 1):
                    if cDF.loc[prevDayWithDay, "est.timezoneOffset"] == \
                      cDF.loc[prevDayWithDay, "home.imputed.timezoneOffset"]:

                        cDF.loc[i, ["est.type"]] = "IMPUTE"

                        cDF.loc[i, ["est.timezoneOffset"]] = \
                            cDF.loc[i, "home.imputed.timezoneOffset"]

                        cDF.loc[i, ["est.timezone"]] = \
                            cDF.loc[i, "home.imputed.timezone"]

                        cDF = addAnnotation(cDF, i, "gap=" + str(gapSize))
                        cDF.loc[i, ["est.gapSize"]] = gapSize

                    else:
                        cDF.loc[i, ["est.type"]] = "UNCERTAIN"
                        cDF = addAnnotation(cDF, i, "unable-to-impute-tzo")
    else:
        cDF["est.type"] = "UNCERTAIN"
        cDF["est.annotations"] = "unable-to-impute-tzo"

    return cDF


def reorderColumns(cDF):
    cDF = cDF[["pump.upload.imputed.timezoneOffset",
               "pump.upload.imputed.timezone",
               "pump.upload.imputed.timeProcessing",
               "cgm.upload.imputed.timezoneOffset",
               "cgm.upload.imputed.timezone",
               "cgm.upload.imputed.timeProcessing",
               "healthkit.upload.imputed.timezoneOffset",
               "healthkit.upload.imputed.timezone",
               "healthkit.upload.imputed.timeProcessing",
               "home.imputed.timezoneOffset",
               "home.imputed.timezone",
               "home.imputed.timeProcessing",
               "upload.timezoneOffset",
               "upload.timezone",
               "upload.timeProcessing",
               "cgm.timezoneOffset",
               "pump.timezoneOffset",
               "date",
               "est.type",
               "est.timezoneOffset",
               "est.timezone",
               "est.timeProcessing",
               "est.annotations",
               "est.gapSize",
               "est.version"]]
    return cDF


def readXlsxData(xlsxPathAndFileName):
    # load xlsx
    df = pd.read_excel(xlsxPathAndFileName, sheet_name=None, ignore_index=True)
    cdf = pd.concat(df.values(), ignore_index=True)
    cdf = cdf.set_index('jsonRowIndex')

    return cdf


def checkInputFile(inputFile):
    if os.path.isfile(inputFile):
        if os.stat(inputFile).st_size > 1000:
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

    return inputData, fileName


def getListOfDSTChangeDays(cDF):

    # get a list of DST change days for the home time zone
    dstChangeDays = \
        cDF[abs(cDF["home.imputed.timezoneOffset"] -
                cDF["home.imputed.timezoneOffset"].shift(-1)) > 0].date

    return dstChangeDays


def correctEstimatesAroundDst(df, cDF):

    # get a list of DST change days for the home time zone
    dstChangeDays = getListOfDSTChangeDays(cDF)

    # loop through the df within 2 days of a daylight savings time change
    for d in dstChangeDays:
        dstIndex = df[(df.date > (d + timedelta(days=-2))) &
                      (df.date < (d + timedelta(days=2)))].index
        for dIdx in dstIndex:
            if pd.notnull(df.loc[dIdx, "est.timezone"]):
                tz = timezone(df.loc[dIdx, "est.timezone"])
                tzRange = getRangeOfTZOsForTimezone(str(tz))
                minHoursToLocal = min(tzRange)/60
                tzoNum = int(tz.localize(df.loc[dIdx, "utcTime"] +
                             timedelta(hours=minHoursToLocal)).strftime("%z"))
                tzoHours = np.floor(tzoNum / 100)
                tzoMinutes = round((tzoNum / 100 - tzoHours) * 100, 0)
                tzoSign = np.sign(tzoHours)
                tzo = int((tzoHours * 60) + (tzoMinutes * tzoSign))
                localTime = \
                    df.loc[dIdx, "utcTime"] + pd.to_timedelta(tzo, unit="m")
                df.loc[dIdx, ["est.localTime"]] = localTime
                df.loc[dIdx, ["est.timezoneOffset"]] = tzo
    return df


def applyLocalTimeEstimates(df, cDF):
    df = pd.merge(df, cDF, how="left", on="date")
    df["est.localTime"] = \
        df["utcTime"] + pd.to_timedelta(df["est.timezoneOffset"], unit="m")

    df = correctEstimatesAroundDst(df, cDF)

    return df


def getLTE(df):
    data = df.copy()
    # PREPROCESS DATA: FILTER, CLEAN, & CORRECT DATA

    # get rid of data that does not have a UTC time
    data = data[data.time.notnull()]

    # get rid of data that does not fall within a valid date range
    # data = filterByDates(data, args.startDate, args.endDate)

    # convert deprecated timezones to their aliases
    timezoneAliases = pd.read_csv("dependencies/wikipedia-timezone-aliases-2018-04-28.csv", low_memory=False)
    data = convertDeprecatedTimezoneToAlias(data, timezoneAliases)

    # apply the large timezone offset correction (AKA Darin's fix)
    data = largeTimezoneOffsetCorrection(data)

    # PREPROCESS DATA: CREATE "DAY" SERIES (cDays)
    # create a continguous-day-series that spans the data date-range
    data["utcTime"] = pd.to_datetime(data.time)
    data["date"] = data["utcTime"].dt.date
    contiguousDays = createContiguousDaySeries(data)

    # create day series for pump, and non-healthkit cgm upload records
    uploadData = getAndPreprocessUploadRecords(data)
    cDays = addDeviceDaySeries(uploadData, contiguousDays, "upload")

    # create day series for cgm data
    cgmData = getAndPreprocessNonDexApiCgmRecords(data)
    cDays = addDeviceDaySeries(cgmData, cDays, "cgm")

    # create day series for pump data
    pumpData = data[(data.type == "bolus") & (data.timezoneOffset.notnull())]
    cDays = addDeviceDaySeries(pumpData, cDays, "pump")

    # interpolate between upload records of the same deviceType, and create a
    # day series for interpolated pump, non-hk-cgm, and healthkit uploads
    for deviceType in ["pump", "cgm", "healthkit"]:
        tempUploadData = uploadData[uploadData.deviceType == deviceType]
        cDays = imputeUploadRecords(tempUploadData, cDays,
                                    deviceType + ".upload.imputed")

    # add a home timezone that also accounts for daylight savings time changes
    cDays = addHomeTimezone(data, cDays)

    # ESTIMATE TIMEZONE OFFSET & TIMEZONE (IF POSSIBLE)
    # There are 3 methods at work here:
    # 1. Use upload records to estimate the TZ and TZO
    # 2. Use device timezone offsets (TZO) to estimate TZO
    # 3. Impute the TZ and TZO using the results from methods 1 and 2

    # 1. USE UPLOAD RECORDS TO ESTIMATE TZ AND TZO
    cDays = estimateTzAndTzoWithUploadRecords(cDays)

    # 2. USE DEVICE TZOs TO ESTIMATE TZO AND TZ (IF POSSIBLE)
    # estimates can be made from pump and cgm data that have a TZO
    # NOTE: the healthkit and dexcom-api cgm data are excluded
    cDays = estimateTzAndTzoWithDeviceRecords(cDays)

    # 3. impute, infer, or interpolate gaps in the estimated tzo and tz
    cDays = imputeTzAndTzo(cDays)

    # APPLY LOCAL TIME ESTIMATES TO ALL DATA
    # postprocess TZ and TZO day estiamte data
    cDays["est.version"] = "0.0.3"
    # reorder columns
    # cDays = reorderColumns(cDays)

    data = applyLocalTimeEstimates(data, cDays)

    return data


def filterByDates(df, startDate, endDate):

    # filter by qualified start & end date, and sort
    df = \
        df[(df.time >= startDate) &
           (df.time <= (endDate + "T23:59:59"))]

    return df


def removeNegativeDurations(df):
    if "duration" in list(df):
        df_durations = df[~(df.type == "physicalActivity")]
        nNegativeDurations = sum(df_durations.duration.astype('float') < 0)
        if nNegativeDurations > 0:
            df = df_durations[~(df_durations.duration.astype('float') < 0)]

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
    
    if "deviceId" in list(df):
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


def cleanData(df):
    data = df.copy()

    # remove negative durations
    data = removeNegativeDurations(data)

    # get rid of cgm values too low/high (< 38 & > 402 mg/dL)
    data, numberOfInvalidCgmValues = removeInvalidCgmValues(data)

    # Tslim calibration bug fix
    data, numberOfTandemAndPayloadCalReadings = tslimCalibrationFix(data)

    return data


def remove_duplicates(df, upload_data):

    df = df.copy()
    upload_data = upload_data.copy()

    # Sort uploads by oldest uploads first
    upload_data = upload_data.sort_values(ascending=True, by="est.localTime")

    # Create an ordered dictionary (i.e. uploadId1 = 1, ,uploadId2 = 2, etc)
    upload_order_dict = dict(
                            zip(upload_data["uploadId"],
                                list(range(1, 1+len(upload_data.uploadId.unique())))
                                )
                            )

    # Sort data by upload order from the ordered dictionary
    # df["upload_order"] = df["uploadId"].copy()
    df["upload_order"] = df["uploadId"].map(upload_order_dict)
    df = df.sort_values(ascending=True, by="upload_order")

    # Replace any healthkit data deviceTimes (NaN) with a unique id
    # This prevents healthkit data with blank deviceTimes from being removed
    if("deviceTime" in list(df)):
        df.deviceTime.fillna(df.id, inplace=True)

    # Drop duplicates using est.localTime+value, time(utc time)+value,
    # deviceTime+value, and est.localTime alone
    # The last entry is kept, which contains the most recent upload data
    values_before_removal = len(df.value)
    df = df.drop_duplicates(subset=["est.localTime", "value"], keep="last")
    df = df.drop_duplicates(subset=["time", "value"], keep="last")
    if("deviceTime" in list(df)):
        df = df.drop_duplicates(subset=["deviceTime", "value"], keep="last")
    df = df.drop_duplicates(subset=["est.localTime"], keep="last")
    values_after_removal = len(df.value)
    duplicates_removed = values_before_removal-values_after_removal

    # Re-sort the data by est.localTime
    df = df.sort_values(ascending=True, by="est.localTime")

    return df, duplicates_removed

# Removes duplicates from 5-minute rounding dataframes
# CGM drops any duplicate that are within 5 minutes of each other (calibrations)
# Bolus combines duplicates that are within 5 minutes of each other
# Basal selects most recent basal from duplicates that are within 5 minutes of each other


def remove_rounded_duplicates(df, data_type):

    new_df = df.copy()
    values_before_removal = len(new_df["est.localTime_rounded"])

    if data_type == "cgm":
        new_df = new_df.drop_duplicates(subset=["est.localTime_rounded"], keep="last")
    elif data_type == "bolus":
        new_df["normal"] = new_df.groupby(by="est.localTime_rounded")["normal"].transform('sum')
        new_df["extended"] = new_df.groupby(by="est.localTime_rounded")["extended"].transform('sum')
        new_df = new_df.drop_duplicates(subset=["est.localTime_rounded"], keep="last")
    else:
        new_df = new_df.drop_duplicates(subset=["est.localTime_rounded"], keep="last")

    values_after_removal = len(new_df["est.localTime_rounded"])
    duplicates_removed = values_before_removal-values_after_removal

    return new_df, duplicates_removed


def fill_basal_gaps(df):

    print("Filling in basal rates...", end=" ")
    # Old Forward Filling Method
    # Fills basal until next basal rate is found
    df["rate"].fillna(method='ffill', inplace=True)

    # Accurate but slow
    # Fill basal by given duration
    # for dur in range(0,len(df.duration)):
    #    if(~np.isnan(df.duration.iloc[dur])):
    #        df.rate.iloc[dur:(dur+int(round(df.duration.iloc[dur]/1000/60/5)))].fillna(method='ffill',inplace=True)

    print("done")
    return df


# Rounds est.localTime data properly
def round5Minutes(df):

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

    timeIntervalMinutes = 5
    timeField = "est.localTime"
    roundedTimeFieldName = "est.localTime_rounded"
    startWithFirstRecord = True,
    verbose = False

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


def create_rounded_time_range(df, first_date, last_date, data_type):

    first_date = pd.to_datetime(dt.datetime.utcfromtimestamp(pd.to_datetime(first_date).timestamp()+.000001)).round("30S")
    first_date = pd.to_datetime(dt.datetime.utcfromtimestamp(pd.to_datetime(first_date).timestamp()+.000001)).round("5min")

    last_date = pd.to_datetime(dt.datetime.utcfromtimestamp(pd.to_datetime(last_date).timestamp()+.000001)).round("30S")
    last_date = pd.to_datetime(dt.datetime.utcfromtimestamp(pd.to_datetime(last_date).timestamp()+.000001)).round("5min")
    # Create 5-min continuous time series in a new dataframe
    five_min_ts = pd.date_range(first_date, last_date, freq="5min")
    new_df = pd.DataFrame({"est.localTime_rounded": five_min_ts})

    # round est.localTime to nearest 5 minutes

    # SLOW BUT MORE ACCURATE
    df = round5Minutes(df)

#    # FAST BUT LESS ACCURATE
#    df["est.localTime_rounded"] = pd.to_datetime(pd.to_datetime(df["est.localTime"]).astype(np.int64)+1000).dt.round("30S")
#    df["est.localTime_rounded"] = pd.to_datetime(pd.to_datetime(df["est.localTime_rounded"]).astype(np.int64)+1000).dt.round("5min")

    df, rounded_duplicates = remove_rounded_duplicates(df.copy(), data_type)
    new_df = pd.merge(new_df, df, on="est.localTime_rounded", how="outer", indicator=True)

    # If basal data, forward fill the rates by duration
    if data_type == "basal":
        fill_basal_gaps(new_df)

    return new_df, rounded_duplicates


def sizeof_fmt(num, suffix='B'):
    ''' By Fred Cirera, after https://stackoverflow.com/a/1094933/1870254'''
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def memory_check():
    for name, size in sorted(((name, sys.getsizeof(value)) for name, value in locals().items()),
                             key=lambda x: -x[1])[:10]:
        print("{:>30}: {:>8}".format(name, sizeof_fmt(size)))
