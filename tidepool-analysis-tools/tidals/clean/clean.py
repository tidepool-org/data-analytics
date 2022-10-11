#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: cleaning tools for tidals (tidepool data analytics tools)
created: 2018-07
author: Ed Nykaza
license: BSD-2-Clause
"""

def remove_duplicates(df, criteriaDF):
    nBefore = len(df)
    df = df.loc[~(criteriaDF.duplicated())]
    df = df.reset_index(drop=True)
    nDuplicatesRemoved = nBefore - len(df)

    return df, nDuplicatesRemoved


def round_time(df, timeIntervalMinutes=5, timeField="time",
               roundedTimeFieldName="roundedTime", verbose=False):
    import pandas as pd
    # A general purpose round time function that rounds the
    # "time" field to nearest <timeIntervalMinutes> minutes
    # INPUTS:
    #   * a dataframe (df) that contains a time field
    #   * timeIntervalMinutes defaults to 5 minutes given that most cgms output every 5 minutes
    #   * timeField defaults to UTC time "time"
    #   * verbose specifies whether the "TIB" and "TIB_cumsum" columns are returned

    df.sort_values(by=timeField, ascending=True, inplace=True)
    df.reset_index(drop=True, inplace=True)

    # calculate the time-in-between (TIB) consecutive records
    t = pd.to_datetime(df[timeField])
    t_shift = pd.to_datetime(df[timeField].shift(1))
    df["TIB"] = round((t - t_shift).dt.days*(86400/(60 * timeIntervalMinutes)) +
                      (t - t_shift).dt.seconds/(60 * timeIntervalMinutes)) * timeIntervalMinutes

    # separate the data into chunks if TIB is greater than <timeIntervalMinutes> minutes
    # so that rounding process can start over
    largeGaps = list(df.query("TIB > " + str(timeIntervalMinutes)).index)
    largeGaps.insert(0, 0)
    largeGaps.append(len(df))

    # loop through each chunk to get the cumulative sum and the rounded time
    for gIndex in range(0, len(largeGaps) - 1):

        df.loc[largeGaps[gIndex], "TIB"] = 0

        df.loc[largeGaps[gIndex]:(largeGaps[gIndex + 1] - 1), "TIB_cumsum"] = \
            df.loc[largeGaps[gIndex]:(largeGaps[gIndex + 1] - 1), "TIB"].cumsum()

        df.loc[largeGaps[gIndex]:(largeGaps[gIndex + 1] - 1), roundedTimeFieldName] = \
            pd.to_datetime(df.loc[largeGaps[gIndex], timeField]).round(str(timeIntervalMinutes) + "min") + \
            pd.to_timedelta(df.loc[largeGaps[gIndex]:(largeGaps[gIndex + 1] - 1), "TIB_cumsum"], unit="m")

    # sort descendingly by time and drop fieldsfields
    df.sort_values(by=timeField, ascending=False, inplace=True)
    df.reset_index(drop=True, inplace=True)
    if verbose is False:
        df.drop(columns=["TIB", "TIB_cumsum"], inplace=True)

    return df


def remove_brackets(df, fieldName):
    if fieldName in list(df):
        df.loc[df[fieldName].notnull(), fieldName] = \
            df.loc[df[fieldName].notnull(), fieldName].str[0]

    return df


def flatten_json(df):
    import pandas as pd
    import numpy as np
    # remove [] from annotations field
    df = remove_brackets(df, "annotations")

    # loop through each columnHeading
    newDataFrame = pd.DataFrame()

    for colHead in list(df):
        # if the df field has embedded json
        if any(isinstance(item, dict) for item in df[colHead]):
            # grab the data that is in brackets
            jsonBlob = df[colHead][df[colHead].astype(str).str[0] == "{"]

            # replace those values with nan
            df.loc[jsonBlob.index, colHead] = np.nan

            # turn jsonBlob to dataframe
            newDataFrame = pd.concat([newDataFrame, pd.DataFrame(jsonBlob.tolist(),
                                      index=jsonBlob.index).add_prefix(colHead + '.')], axis=1)

    df = pd.concat([df, newDataFrame], axis=1)

    return df
