#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: Run a full analysis of T1DX Survey Participant Data
version: 0.0.3
created: 2018-10-28
author: Jason Meno
dependencies:
    * requires environmental variables: import environmentalVariables.py
license: BSD-2-Clause
"""

import os
from os.path import join, dirname, isfile
from dotenv import load_dotenv
import pandas as pd
import datetime as dt
import numpy as np
import sys
import requests
import json
import hashlib
from pytz import timezone
from datetime import timedelta
import pdb


# %% Functions
def accept_new_donor(email, password):
    nAccepted = 0
    url1 = "https://api.tidepool.org/auth/login"
    myResponse = requests.post(url1, auth=(email, password))

    if(myResponse.ok):
        xtoken = myResponse.headers["x-tidepool-session-token"]
        userid = json.loads(myResponse.content.decode())["userid"]
        url2 = "https://api.tidepool.org/confirm/invitations/" + userid
        headers = {
            "x-tidepool-session-token": xtoken,
            "Content-Type": "application/json"
        }

        myResponse2 = requests.get(url2, headers=headers)
        if(myResponse2.ok):

            usersData = json.loads(myResponse2.content.decode())

            for i in range(0, len(usersData)):
                shareKey = usersData[i]["key"]
                shareID = usersData[i]["creatorId"]
                payload = {
                    "key": shareKey
                }

                url3 = "https://api.tidepool.org/confirm/accept/invite/" + \
                    userid + "/" + shareID

                myResponse3 = requests.put(url3, headers=headers, json=payload)

                if(myResponse3.ok):
                    nAccepted = nAccepted + 1
                else:
                    print(email, "ERROR", myResponse3.status_code)
                    sys.exit("Error with " + email + ":" + str(myResponse3.status_code))
        elif myResponse2.status_code == 404:
            # this is the case where there are no new invitations
            print("very likely that no new invitations exist")
        else:
            print(email, "ERROR", myResponse2.status_code)
            sys.exit("Error with " + email + ":" + str(myResponse2.status_code))
    else:
        print(email, "ERROR", myResponse.status_code)
        sys.exit("Error with " + email + ":" + str(myResponse.status_code))

    return nAccepted


def get_donor_info(email, password, donorMetadataColumns):
    donorMetaData = pd.DataFrame(columns=donorMetadataColumns)
    url1 = "https://api.tidepool.org/auth/login"
    myResponse = requests.post(url1, auth=(email, password))

    if(myResponse.ok):
        xtoken = myResponse.headers["x-tidepool-session-token"]
        userid = json.loads(myResponse.content.decode())["userid"]
        url2 = "https://api.tidepool.org/metadata/users/" + userid + "/users"
        headers = {
            "x-tidepool-session-token": xtoken,
            "Content-Type": "application/json"
        }

        myResponse2 = requests.get(url2, headers=headers)
        if(myResponse2.ok):

            usersData = json.loads(myResponse2.content.decode())

            for i in range(0, len(usersData)):
                userID = usersData[i]["userid"]
                userName = usersData[i]["profile"]["fullName"]
                userEmail = usersData[i]["username"]

                try:
                    bDay = usersData[i]["profile"]["patient"]["birthday"]
                except Exception:
                    bDay = np.nan
                try:
                    dDay = usersData[i]["profile"]["patient"]["diagnosisDate"]
                except Exception:
                    dDay = np.nan
                try:
                    diagnosisType = usersData[i]["profile"]["patient"]["diagnosisType"]
                except Exception:
                    diagnosisType = np.nan
                try:
                    targetDevices = usersData[i]["profile"]["patient"]["targetDevices"]
                except Exception:
                    targetDevices = np.nan
                try:
                    targetTimezone = usersData[i]["profile"]["patient"]["targetTimezone"]
                except Exception:
                    targetTimezone = np.nan
                try:
                    termsAccepted = usersData[i]["termsAccepted"]
                except Exception:
                    termsAccepted = np.nan

                usr_string = userEmail.lower() + os.environ["SALT"]

                hash_user = hashlib.sha256(usr_string.encode())
                hashID = hash_user.hexdigest()
                donorMetaData = donorMetaData.append(
                        pd.DataFrame([[userID,
                                       userName,
                                       userEmail,
                                       bDay,
                                       dDay,
                                       diagnosisType,
                                       targetDevices,
                                       targetTimezone,
                                       termsAccepted,
                                       hashID]],
                                     columns=donorMetadataColumns),
                                     ignore_index=True)
        else:
            print(donorGroup, "ERROR", myResponse2.status_code)
            sys.exit("Error: " + str(myResponse2.status_code))
    else:
        print(donorGroup, "ERROR", myResponse.status_code)
        sys.exit("Error: " + str(myResponse.status_code))

    return donorMetaData


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
    print("Removing", data_type, "rounded duplicates...", end=" ")

    new_df = df.copy()
    values_before_removal = len(new_df["est.localTime_rounded"])

    if data_type == "cgm":
        new_df = new_df.drop_duplicates(subset=["est.localTime_rounded"], keep="last")
        new_df["mg_dL"] = (new_df.value*18.01559).astype(int)
    elif data_type == "bolus":
        new_df["normal"] = new_df.groupby(by="est.localTime_rounded")["normal"].transform('sum')
        new_df["extended"] = new_df.groupby(by="est.localTime_rounded")["extended"].transform('sum')
        new_df = new_df.drop_duplicates(subset=["est.localTime_rounded"], keep="last")
    else:
        new_df = new_df.drop_duplicates(subset=["est.localTime_rounded"], keep="last")

    values_after_removal = len(new_df["est.localTime_rounded"])
    duplicates_removed = values_before_removal-values_after_removal
    print("done")

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
    timeField = "time"
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

    print("Creating rounded", data_type, "time ranges...", end=" ")
    first_date = pd.to_datetime(dt.datetime.fromtimestamp(pd.to_datetime(first_date).timestamp()+.000001)).round("30S")
    first_date = pd.to_datetime(dt.datetime.fromtimestamp(pd.to_datetime(first_date).timestamp()+.000001)).round("5min")

    last_date = pd.to_datetime(dt.datetime.fromtimestamp(pd.to_datetime(last_date).timestamp()+.000001)).round("30S")
    last_date = pd.to_datetime(dt.datetime.fromtimestamp(pd.to_datetime(last_date).timestamp()+.000001)).round("5min")
    # Create 5-min continuous time series in a new dataframe
    five_min_ts = pd.date_range(first_date, last_date, freq="5min")
    new_df = pd.DataFrame({"est.localTime_rounded": five_min_ts})

    # round est.localTime to nearest 5 minutes

    # SLOW BUT MORE ACCURATE
    df = round5Minutes(df)

#    # FAST BUT LESS ACCURATE
#    df["est.localTime_rounded"] = pd.to_datetime(pd.to_datetime(df["est.localTime"]).astype(np.int64)+1000).dt.round("30S")
#    df["est.localTime_rounded"] = pd.to_datetime(pd.to_datetime(df["est.localTime_rounded"]).astype(np.int64)+1000).dt.round("5min")

    print("done")

    df, rounded_duplicates = remove_rounded_duplicates(df.copy(), data_type)
    new_df = pd.merge(new_df, df, on="est.localTime_rounded", how="outer", indicator=True)

    # If basal data, forward fill the rates by duration
    if data_type == "basal":
        fill_basal_gaps(new_df)

    return new_df, rounded_duplicates


def get_rolling_stats(df, rolling_prefixes):

    print("Preparing Variables... ", end=" ")

    # Functions to calculate average daily hypo/hyper events and duration
    def rle(inarray):
        """ run length encoding. Partial credit to R rle function.
            Multi datatype arrays catered for including non Numpy
            returns: tuple (runlengths, startpositions, values) """
        ia = np.asarray(inarray)                  # force numpy
        n = len(ia)
        if n == 0:
            return (None, None, None)
        else:
            y = np.array(ia[1:] != ia[:-1])      # pairwise unequal (string safe)
            i = np.append(np.where(y), n - 1)    # must include last element posi
            z = np.diff(np.append(-1, i))        # run lengths
            p = np.cumsum(np.append(0, z))[:-1]  # positions
            return(z, p, ia[i])

    # Setup run length encoding for hypo/hyper events
    rle_below54 = rle(df.mg_dL < 54)
    rle_below70 = rle(df.mg_dL < 70)
    rle_above140 = rle(df.mg_dL > 140)
    rle_above180 = rle(df.mg_dL > 180)
    rle_above250 = rle(df.mg_dL > 250)

    col_names = ["event-below54",
                 "dur-below54",
                 "event-below70",
                 "dur-below70",
                 "event-above140",
                 "dur-above140",
                 "event-above180",
                 "dur-above180",
                 "event-above250",
                 "dur-above250"]

    df.reindex(columns=[df.columns.tolist()+col_names])
    # Start getting locations and durations of hypo/hyper episodes
    # Note: Error 712 is common here due to bool checks in a numpy function
    # See https://github.com/PyCQA/pycodestyle/issues/450

    below54_loc = rle_below54[1][np.where((rle_below54[2] == True) & (rle_below54[0] >= 3))]
    below54_dur = 5*rle_below54[0][np.where((rle_below54[2] == True) & (rle_below54[0] >= 3))]
    df["event-below54"] = False
    df.loc[below54_loc, "event-below54"] = True
    df["dur-below54"] = 0
    df.loc[below54_loc, "dur-below54"] = below54_dur

    below70_loc = rle_below70[1][np.where((rle_below70[2] == True) & (rle_below70[0] >= 3))]
    below70_dur = 5*rle_below70[0][np.where((rle_below70[2] == True) & (rle_below70[0] >= 3))]
    df["event-below70"] = False
    df.loc[below70_loc, "event-below70"] = True
    df["dur-below70"] = 0
    df.loc[below70_loc, "dur-below70"] = below70_dur

    above140_loc = rle_above140[1][np.where((rle_above140[2] == True) & (rle_above140[0] >= 3))]
    above140_dur = 5*rle_above140[0][np.where((rle_above140[2] == True) & (rle_above140[0] >= 3))]
    df["event-above140"] = False
    df.loc[above140_loc, "event-above140"] = True
    df["dur-above140"] = 0
    df.loc[above140_loc, "dur-above140"] = above140_dur

    above180_loc = rle_above180[1][np.where((rle_above180[2] == True) & (rle_above180[0] >= 3))]
    above180_dur = 5*rle_above180[0][np.where((rle_above180[2] == True) & (rle_above180[0] >= 3))]
    df["event-above180"] = False
    df.loc[above180_loc, "event-above180"] = True
    df["dur-above180"] = 0
    df.loc[above180_loc, "dur-above180"] = above180_dur

    above250_loc = rle_above250[1][np.where((rle_above250[2] == True) & (rle_above250[0] >= 3))]
    above250_dur = 5*rle_above250[0][np.where((rle_above250[2] == True) & (rle_above250[0] >= 3))]
    df["event-above250"] = False
    df.loc[above250_loc, "event-above250"] = True
    df["dur-above250"] = 0
    df.loc[above250_loc, "dur-above250"] = above250_dur

    df["bool_below54"] = df.mg_dL < 54
    df["bool_54-70"] = (df.mg_dL >= 54) & (df.mg_dL <= 70)
    df["bool_below70"] = df.mg_dL < 70
    df["bool_70-140"] = (df.mg_dL >= 70) & (df.mg_dL <= 140)
    df["bool_70-180"] = (df.mg_dL >= 70) & (df.mg_dL <= 180)
    df["bool_above180"] = df.mg_dL > 180
    df["bool_above250"] = df.mg_dL > 250

    # Setup curves of value ranges to integrate over for AUC metrics
    df["below54_vals"] = df.loc[df["bool_below54"], "mg_dL"]
    df["below54_vals"].fillna(0, inplace=True)
    df["54-70_vals"] = df.loc[df["bool_54-70"], "mg_dL"]
    df["54-70_vals"].fillna(0, inplace=True)
    df["below70_vals"] = df.loc[df["bool_below70"], "mg_dL"]
    df["below70_vals"].fillna(0, inplace=True)
    df["70-140_vals"] = df.loc[df["bool_70-140"], "mg_dL"]-70
    df["70-140_vals"].fillna(0, inplace=True)
    df["70-180_vals"] = df.loc[df["bool_70-180"], "mg_dL"]-70
    df["70-180_vals"].fillna(0, inplace=True)
    df["above180_vals"] = df.loc[df["bool_above180"], "mg_dL"]-180
    df["above180_vals"].fillna(0, inplace=True)
    df["above250_vals"] = df.loc[df["bool_above250"], "mg_dL"]-250
    df["above250_vals"].fillna(0, inplace=True)

    # Setup sleep data (12AM-6AM)
    sleep_bool = (df["est.localTime"].dt.hour*60+df["est.localTime"].dt.minute) < 360
    df["sleep_values"] = df.loc[sleep_bool, "mg_dL"]

    # Map Dictionary of rolling window sizes
    rolling_dictionary = \
        dict(zip(
            ["15min", "30min", "1hr", "2hr", "3hr", "4hr", "5hr", "6hr", "8hr",
             "12hr", "24hr", "3day", "7day", "14day", "30day", "60day",
             "90day", "1year"], list(
             [3, 6, 12, 24, 36, 48, 60, 72, 96,
              144, 288, 864, 2016, 4032, 8640, 17280,
              25920, 105120]
                 )))

    # Set number of points per rolling window
    rolling_points = np.array(pd.Series(rolling_prefixes).map(rolling_dictionary))
    # Set minimum percentage of points required to calculate rolling statistic
    percent_points = 0.7
    rolling_min = np.floor(percent_points*rolling_points).astype(int)

    print("done")

    print("Starting Rolling Stats")
    rolling_df = pd.DataFrame(index=np.arange(len(df)))
    rolling_df["est.localTime_rounded"] = df["est.localTime_rounded"]

    # Loop through rolling stats for each time prefix
    for prefix_loc in range(0, len(rolling_prefixes)):

        # start_time = time.time()
        rolling_window = df.mg_dL.rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc])

        rolling_df[rolling_prefixes[prefix_loc]+"_data-points"] = rolling_window.count()
        rolling_df[rolling_prefixes[prefix_loc]+"_percent-data-available"] = rolling_df[rolling_prefixes[prefix_loc]+"_data-points"]/rolling_points[prefix_loc]
        rolling_df[rolling_prefixes[prefix_loc]+"_mean"] = rolling_window.mean()
        # get estimated HbA1c or Glucose Management Index (GMI)
        # GMI(%) = 3.31 + 0.02392 x [mean glucose in mg/dL]
        # https://www.jaeb.org/gmi/
        rolling_df[rolling_prefixes[prefix_loc]+"_GMI"] = 3.31 + (0.02392*rolling_df[rolling_prefixes[prefix_loc]+"_mean"])
        rolling_df[rolling_prefixes[prefix_loc]+"_SD"] = rolling_window.std()
        rolling_df[rolling_prefixes[prefix_loc]+"_CV"] = rolling_df[rolling_prefixes[prefix_loc]+"_SD"]/rolling_df[rolling_prefixes[prefix_loc]+"_mean"]
        rolling_df[rolling_prefixes[prefix_loc]+"_percent-below54"] = df["bool_below54"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_data-points"]
        rolling_df[rolling_prefixes[prefix_loc]+"_percent-54-70"] = df["bool_54-70"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_data-points"]
        rolling_df[rolling_prefixes[prefix_loc]+"_percent-below70"] = df["bool_below70"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_data-points"]
        rolling_df[rolling_prefixes[prefix_loc]+"_percent-70-140"] = df["bool_70-140"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_data-points"]
        rolling_df[rolling_prefixes[prefix_loc]+"_percent-70-180"] = df["bool_70-180"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_data-points"]
        rolling_df[rolling_prefixes[prefix_loc]+"_percent-above180"] = df["bool_above180"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_data-points"]
        rolling_df[rolling_prefixes[prefix_loc]+"_percent-above250"] = df["bool_above250"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_data-points"]
        rolling_df[rolling_prefixes[prefix_loc]+"_min"] = rolling_window.min()

        # Quartiles take a long time to process.
        # Uncomment if needed

        rolling_df[rolling_prefixes[prefix_loc]+"_10percentile"] = rolling_window.quantile(0.1)
        rolling_df[rolling_prefixes[prefix_loc]+"_25percentile"] = rolling_window.quantile(0.25)
        rolling_df[rolling_prefixes[prefix_loc]+"_50percentile"] = rolling_window.quantile(0.5)
        rolling_df[rolling_prefixes[prefix_loc]+"_75percentile"] = rolling_window.quantile(0.75)
        rolling_df[rolling_prefixes[prefix_loc]+"_90percentile"] = rolling_window.quantile(0.9)
        rolling_df[rolling_prefixes[prefix_loc]+"_max"] = rolling_window.max()
        rolling_df[rolling_prefixes[prefix_loc]+"_IQR"] = rolling_df[rolling_prefixes[prefix_loc]+"_75percentile"] - rolling_df[rolling_prefixes[prefix_loc]+"_25percentile"]

        rolling_df[rolling_prefixes[prefix_loc]+"_events-below54"] = df["event-below54"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()
        rolling_df[rolling_prefixes[prefix_loc]+"_avg-time-below54"] = df["dur-below54"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_events-below54"]
        rolling_df[rolling_prefixes[prefix_loc]+"_events-below70"] = df["event-below70"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()
        rolling_df[rolling_prefixes[prefix_loc]+"_avg-time-below70"] = df["dur-below70"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_events-below70"]
        rolling_df[rolling_prefixes[prefix_loc]+"_events-above140"] = df["event-above140"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()
        rolling_df[rolling_prefixes[prefix_loc]+"_avg-time-above140"] = df["dur-above140"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_events-above140"]
        rolling_df[rolling_prefixes[prefix_loc]+"_events-above180"] = df["event-above180"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()
        rolling_df[rolling_prefixes[prefix_loc]+"_avg-time-above180"] = df["dur-above180"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_events-above180"]
        rolling_df[rolling_prefixes[prefix_loc]+"_events-above250"] = df["event-above250"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()
        rolling_df[rolling_prefixes[prefix_loc]+"_avg-time-above250"] = df["dur-above250"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_events-above250"]
        
        rolling_df[rolling_prefixes[prefix_loc]+"_AUC-avg_below54"] = df["below54_vals"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).apply(lambda x: np.trapz(x, dx=5), raw=True)/(rolling_points[prefix_loc]/288)
        rolling_df[rolling_prefixes[prefix_loc]+"_AUC-avg_below70"] = df["below70_vals"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).apply(lambda x: np.trapz(x, dx=5), raw=True)/(rolling_points[prefix_loc]/288)
        rolling_df[rolling_prefixes[prefix_loc]+"_AUC-avg_70-140"] = df["70-140_vals"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).apply(lambda x: np.trapz(x, dx=5), raw=True)/(rolling_points[prefix_loc]/288)
        rolling_df[rolling_prefixes[prefix_loc]+"_AUC-avg_70-180"] = df["70-180_vals"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).apply(lambda x: np.trapz(x, dx=5), raw=True)/(rolling_points[prefix_loc]/288)
        rolling_df[rolling_prefixes[prefix_loc]+"_AUC-avg_above180"] = df["above180_vals"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).apply(lambda x: np.trapz(x, dx=5), raw=True)/(rolling_points[prefix_loc]/288)
        rolling_df[rolling_prefixes[prefix_loc]+"_AUC-avg_above250"] = df["above250_vals"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).apply(lambda x: np.trapz(x, dx=5), raw=True)/(rolling_points[prefix_loc]/288)

        rolling_df[rolling_prefixes[prefix_loc]+"_LBGI"] = np.nan
        rolling_df[rolling_prefixes[prefix_loc]+"_HBGI"] = np.nan

        # Sleep specific rolling stats
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep_data-points"] = df["sleep_values"].rolling(rolling_points[prefix_loc], min_periods=1).count()
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep_percent-data-available"] = rolling_df[rolling_prefixes[prefix_loc]+"_sleep_data-points"]/(72*rolling_points[prefix_loc]/288)
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep_mean"] = df["sleep_values"].rolling(rolling_points[prefix_loc], min_periods=1).mean()
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep_SD"] = df["sleep_values"].rolling(rolling_points[prefix_loc], min_periods=1).std()
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep_CV"] = rolling_df[rolling_prefixes[prefix_loc]+"_sleep_SD"]/rolling_df[rolling_prefixes[prefix_loc]+"_sleep_mean"]

        # TODO: Provide the proper calculations for metrics below
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep_percent-below54"] = np.nan
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep_percent-54-70"] = np.nan
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep_percent-below70"] = np.nan
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep_percent-70-140"] = np.nan
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep_percent-70-180"] = np.nan
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep_percent-above180"] = np.nan
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep_percent-above250"] = np.nan

        rolling_df[rolling_prefixes[prefix_loc]+"_sleep_events-below54"] = np.nan
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep_avg-time-below54"] = np.nan
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep_events-below70"] = np.nan
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep_avg-time-below70"] = np.nan
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep_events-above140"] = np.nan
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep_avg-time-above140"] = np.nan
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep_events-above180"] = np.nan
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep_avg-time-above180"] = np.nan
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep_events-above250"] = np.nan
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep_avg-time-above250"] = np.nan

        rolling_df[rolling_prefixes[prefix_loc]+"_sleep_LBGI"] = np.nan
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep_HBGI"] = np.nan
        # print(rolling_prefixes[prefix_loc], ' took {0} seconds.'.format(time.time() - start_time))

    return rolling_df


def get_daily_stats(df, daytime_start):

    daily_df = df.copy()
    daily_df.set_index("est.localTime_rounded", inplace=True)

    # Isolate all statistics to just rows at daytime_start (default 5:55)
    daily_df = daily_df.at_time(daytime_start)

    # Move time back 6 hours so that each row represents the appropriate day
    daily_df.index = daily_df.index-dt.timedelta(hours=6)

    return daily_df


def get_summary_stats(hashID, df, day_df):
    summary_df = pd.DataFrame(columns=day_df.columns.tolist())
    summary_df.loc[0] = day_df.iloc[-1]
    summary_df["hashID"] = hashID
    summary_df.set_index("hashID", inplace=True)
    first_ts = str(pd.to_datetime(final_df.loc[final_df.value.notnull(), "est.localTime"]).min())
    last_ts = str(pd.to_datetime(final_df.loc[final_df.value.notnull(), "est.localTime"]).max())
    summary_df.insert(0, "first_ts", first_ts)
    summary_df.insert(1, "last_ts", last_ts)

    return summary_df


def validate_study_criteria(df, endDate):
    # Check if at least at least three months (28*3 days) of data >= 70% filled
    three_month_min_points = int(84*288*0.7)
    three_month_startDate = str(pd.to_datetime(endDate) - pd.Timedelta(days=84))

    df = df[(df["est.localTime"] >= three_month_startDate) & (df["est.localTime"] <= (endDate))]

    criteria_bool = df.value.count() >= three_month_min_points

    # Check if at least 5 days of data per week >= 70% filled in the last month
    weekly_min_points = int(7*288*0.7)
    weekly_endDate = endDate

    for week_num in range(4):
        weekly_startDate = str(pd.to_datetime(weekly_endDate) - pd.Timedelta(days=7))
        weekly_df = df[(df["est.localTime"] >= weekly_startDate) & (df["est.localTime"] <= (weekly_endDate))]
        criteria_bool = criteria_bool * (weekly_df.value.count() >= weekly_min_points)
        weekly_endDate = weekly_startDate

    return criteria_bool


# %% load environmental variables
dotenv_path = join(dirname(__file__), '.env')
if isfile(dotenv_path):
    load_dotenv(dotenv_path)

survey_data = pd.read_excel(os.path.join(".", "data", "survey_results.xlsx"))

# Create an analyzed column to mark datasets already analyzed
currentDate = dt.datetime.now().strftime("%Y-%m-%d")

if("Time Started" not in list(survey_data)):
    survey_data["Time Started"] = currentDate

survey_data = survey_data[["Hashed ID", "Time Started"]]
# Create a column to mark user in Tidepool
survey_data["Tidepool Account"] = False

# Create a column to mark data sharing in Tidepool
survey_data["Data Uploaded"] = False

# Create a column to mark CGM data available in Tidepool
survey_data["CGM Data"] = False

# Create a column to mark CGM data available in Tidepool
survey_data["Data Qualifies"] = False

# Create an analyzed column to mark datasets already analyzed
survey_data["analyzed"] = False

timezoneAliasesFilePathAndName = os.path.join(".", "wikipedia-timezone-aliases-2018-04-28.csv")
if os.path.isfile(timezoneAliasesFilePathAndName):
    timezoneAliases = pd.read_csv(timezoneAliasesFilePathAndName, low_memory=False)
else:
    sys.exit("{0} is not a valid file".format(timezoneAliasesFilePathAndName))

skip_analysis = False

# Create cleaned data directory if it doesn't exist
clean_data_path = os.path.join(".", "data", "cleaned-donor-data")
if not os.path.exists(clean_data_path):
    os.mkdir(clean_data_path)

# %% Accept New Donors
new_donors = accept_new_donor(os.environ["EMAIL"], os.environ["PASS"])


# %% Get Account Donor List
donorMetadataColumns = ["userID", "name", "email",
                        "bDay", "dDay", "diagnosisType",
                        "targetDevices", "targetTimezone",
                        "termsAccepted", "hashID"]

alldonorMetadataList = pd.DataFrame(columns=donorMetadataColumns)

study_donor_list = get_donor_info(os.environ["EMAIL"], os.environ["PASS"], donorMetadataColumns)

# Track Tidepool account survey taken status
study_donor_list["survey_taken"] = False
# %% Start Main Loop for donors

for donor_row in range(len(study_donor_list)):

    # Get study userID and hashID
    studyUserID = study_donor_list.loc[donor_row, "userID"]
    studyHashID = study_donor_list.loc[donor_row, "hashID"]

    # Run pipeline if donor data is available and has not been analyzed
    if (studyHashID in list(survey_data["Hashed ID"])):
        study_donor_list.loc[donor_row, "survey_taken"] = True
        previously_analyzed = survey_data.loc[survey_data["Hashed ID"] == studyHashID, "analyzed"].values[0]

        if(previously_analyzed):
            print(studyHashID + " already analyzed.\n")
            print("COMPLETED " + str(donor_row+1) +
                  "/" + str(len(study_donor_list)) + "\n")
            continue

        survey_data.loc[survey_data["Hashed ID"] == studyHashID, "Tidepool Account"] = True

        print(studyHashID + " START PROCESSING")
        # Get timestamps of when survey was taken
        # and up to one year prior
        endDate = pd.to_datetime(survey_data.loc[survey_data["Hashed ID"] == studyHashID, "Time Started"].values[0])
        startDate = pd.to_datetime(endDate) - pd.Timedelta(days=365)
        endDate = str(endDate)
        startDate = str(startDate)
        file_outpath = os.path.join(clean_data_path, "PHI-"+studyHashID+".xlsx")

        if(os.path.isfile(file_outpath)):
            final_df = pd.read_excel(file_outpath)
            survey_data.loc[survey_data["Hashed ID"] == studyHashID, "CGM Data"] = True

        else:
            # Get data
            data = get_user_data(os.environ["EMAIL"], os.environ["PASS"], studyUserID)

            if("time" not in list(data)):
                print(studyHashID + " NO DATA IN ACCOUNT.\n")
                print("COMPLETED " + str(donor_row+1) +
                      "/" + str(len(study_donor_list)) + "\n")
                continue

            if(skip_analysis):
                survey_data.loc[survey_data["Hashed ID"] == studyHashID, "Data Uploaded"] = True
                survey_data.loc[survey_data["Hashed ID"] == studyHashID, "analyzed"] = True
                print("COMPLETED " + str(donor_row+1) +
                      "/" + str(len(study_donor_list)) + "\n")
                continue

            # Estimate Local Time
            data = getLTE(data)

            if("deviceTime" in list(data)):
                # Fill localTime with deviceTime if getLTE cannot impute (NaT)
                # and deviceTime comes from Dexcom API
                data["est.localTime"].fillna(pd.to_datetime(data.loc[data["isDexcomAPI"], "deviceTime"]), inplace=True)

            # Clean Data
            data = cleanData(data)

            # Filter Data to before survey was taken
            data = data[(data["est.localTime"] >= startDate) & (data["est.localTime"] <= (endDate))]

            # Extract cgm and upload data
            cgm_df = data.loc[data.type == "cbg"]
            upload_df = data.loc[data.type == "upload"]

            if(len(cgm_df) == 0):

                print(studyHashID + " NO CGM data available.\n")
                continue

            survey_data.loc[survey_data["Hashed ID"] == studyHashID, "CGM Data"] = True

            cgm_df, cgm_duplicate_count = remove_duplicates(cgm_df, upload_df)

            cgm_df, cgm_rounded_duplicate_count = create_rounded_time_range(cgm_df, startDate, endDate, "cgm")

            final_df = cgm_df.copy()

            # Export data frame to user file
            final_df.to_excel(file_outpath, index=False)

        # Verify cgm data is valid for study
        cgm_data_validated_bool = validate_study_criteria(final_df, endDate)
        survey_data.loc[survey_data["Hashed ID"] == studyHashID, "Data Qualifies"] = cgm_data_validated_bool

        rolling_window = ["7day", "14day", "30day", "90day", "1year"]
        day_start = "5:55"

        rolling_df = get_rolling_stats(final_df, rolling_window)
        daily_df = get_daily_stats(rolling_df, day_start)
        summary_df = get_summary_stats(studyHashID, final_df, daily_df)

        outputFileName = "Tidepool-T1DX-Analytics-Results-" + currentDate + ".csv"
        summary_path = os.path.join(".", "data", outputFileName)

        if not os.path.exists(summary_path):
            summary_df.to_csv(summary_path, header=True)
        else:
            summary_df.to_csv(summary_path, mode='a', header=False)

        survey_data.loc[survey_data["Hashed ID"] == studyHashID, "Data Uploaded"] = True
        survey_data.loc[survey_data["Hashed ID"] == studyHashID, "analyzed"] = True

        print("COMPLETED " + str(donor_row+1) +
              "/" + str(len(study_donor_list)) + "\n")
    else:
        print(studyHashID + " survey data not available.\n")
        print("COMPLETED " + str(donor_row+1) +
              "/" + str(len(study_donor_list)) + "\n")

# Analysis Run Summary
survey_count = len(survey_data)
account_and_survey = study_donor_list["survey_taken"].sum()
account_no_survey = len(study_donor_list) - account_and_survey
analyzed_count = survey_data.analyzed.sum()
missing_data_count = survey_count - analyzed_count
accounts_qualified = survey_data["Data Qualifies"].sum()
print("Survey Participants: " + str(survey_count))
print("Data Sets analyzed:  " + str(analyzed_count))
print("No Data in Tidepool: " + str(missing_data_count))
print("Survey & in Tidepool: " + str(account_and_survey))
print("In Tidepool & No Survey: " + str(account_no_survey))
print("Accounts Qualified:" + str(accounts_qualified))

survey_data["Contact?"] = np.nan

# Filter survey output
survey_data = survey_data[["Hashed ID",
                           "Time Started",
                           "Tidepool Account",
                           "Data Uploaded",
                           "CGM Data",
                           "Data Qualifies",
                           "Contact?"]]

phi_lookup_table = study_donor_list[["hashID", "name", "email"]]

for survey_row in range(len(survey_data)):
    if(survey_data.loc[survey_row, "Tidepool Account"]):
        if(survey_data.loc[survey_row, "Data Uploaded"] and survey_data.loc[survey_row, "CGM Data"]):
                continue
        else:
            survey_data.loc[survey_row, "Contact?"] = "Tidepool"
    else:
        survey_data.loc[survey_row, "Contact?"] = "T1DX"

survey_data.to_excel(os.path.join(".", "data", "survey_data_status_" + currentDate + ".xlsx"), index=False)
phi_lookup_table.to_excel(os.path.join(".", "data", "PHI-T1DX_Tidepool_Pilot_Accounts.xlsx"), index=False)