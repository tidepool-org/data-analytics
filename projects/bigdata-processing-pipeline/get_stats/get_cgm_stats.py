#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
calculate cgm statsistics for a single tidepool (donor) dataset
'''


# %% REQUIRED LIBRARIES
import os
import sys
import hashlib
import pytz
import numpy as np
import pandas as pd
import datetime as dt

# TODO: figure out how to get rid of these path dependcies
get_donor_data_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
if get_donor_data_path not in sys.path:
    sys.path.insert(0, get_donor_data_path)
import environmentalVariables
from get_donor_data.get_single_donor_metadata import get_shared_metadata
from get_donor_data.get_single_tidepool_dataset import get_data


# %% CONSTANTS
MGDL_PER_MMOLL = 18.01559


# %% FUNCTIONS
'''
the functions that are called in this script,
which includes notes of where the functions came from,
and whether they were refactored
'''


def hash_userid(userid, salt):
    '''
    taken from anonymize-and-export.py
    refactored name(s) to meet style guide
    '''
    usr_string = userid + salt
    hash_user = hashlib.sha256(usr_string.encode())
    hashid = hash_user.hexdigest()

    return hashid


def get_type(val):
    return type(val).__name__


def remove_negative_durations(df):
    '''
    taken from https://github.com/tidepool-org/data-analytics/blob/
    etn/get-settings-and-events/projects/get-donors-pump-settings/
    get-users-settings-and-events.py

    refactored name(s) to meet style guide
    refactored pandas field call to df["field"] instead of df.field
    refactored because physical activity includes embedded json, whereas
    the other fields in the data model require a integer
    '''
    if "duration" in list(df):
        type_ = df["duration"].apply(get_type)
        valid_index = ((type_ == "int") & (df["duration"].notnull()))
        n_negative_durations = sum(df.loc[valid_index, "duration"] < 0)
        if n_negative_durations > 0:
            df = df[~(df.loc[valid_index, "duration"] < 0)]
    else:
        n_negative_durations = np.nan

    return df, n_negative_durations


def expand_embedded_dict(ts, key_):
    '''Expanded a single field that has embedded json

    Args:
        ts: a pandas time series of the field that has embedded json
        key_: the key that you want to expand

    Raise:
        TypeError: if you don't pass in a pandas time series

    Returns:
        key_ts: a new time series of the key of interest

    NOTE:
        this is new function
    TODO:
        could be refactored to allow multiple keys or all keys to be returned
        could be refactored for speed as the current process
    '''

    if "Series" not in type(ts).__name__:
        raise TypeError('Expecting a pandas time series object')
    key_ts = pd.Series(name=ts.name + "." + key_, index=ts.index)
    notnull_idx = ts.notnull()
    # TODO: maybe sped up by only getting the one field of interest?
    # though, the current method is fairly quick and compact
    temp_df = pd.DataFrame(ts[notnull_idx].tolist())
    if key_ in list(temp_df):
        key_ts[notnull_idx] = temp_df[key_].values

    return key_ts


def get_embedded_field(ts, embedded_field):
    '''get a field that is nested in more than 1 embedded dictionary (json)

    Args:
        ts: a pandas time series of the field that has embedded json
        embedded_field (str): the location of the field that is deeply nested
            (e.g., "origin.payload.device.model")

    Raise:
        ValueError: if you don't pass in a pandas time series

    Returns:
        new_ts: a new time series of the key of interest

    NOTE:
        this is new function
        the "." notation is used to reference nested json

    '''
    field_list = embedded_field.split(".")
    if len(field_list) < 2:
        raise ValueError('Expecting at least 1 embedded field')

    new_ts = expand_embedded_dict(ts, field_list[1])
    for i in range(2, len(field_list)):
        new_ts = expand_embedded_dict(new_ts, field_list[i])

    return new_ts


def tslim_calibration_fix(df):
    '''
    taken from https://github.com/tidepool-org/data-analytics/blob/
    etn/get-settings-and-events/projects/get-donors-pump-settings/
    get-users-settings-and-events.py

    refactored name(s) to meet style guide
    refactored pandas field call to df["field"] instead of df.field
    refactored to only expand one field
    '''

    # expand payload field one level
    df["payload.calibration_reading"] = (
        expand_embedded_dict(df["payload"], "calibration_reading")
    )

    if df["payload.calibration_reading"].notnull().sum() > 0:

        search_for = ['tan']
        tandem_data_index = (
            (df["deviceId"].str.contains('|'.join(search_for)))
            & (df["type"] == "deviceEvent")
        )

        cal_index = df["payload.calibration_reading"].notnull()
        valid_index = tandem_data_index & cal_index

        n_cal_readings = sum(valid_index)

        if n_cal_readings > 0:
            # if reading is > 30 then it is in the wrong units
            if df["payload.calibration_reading"].min() > 30:
                df.loc[cal_index, "value"] = (
                    df.loc[valid_index, "payload.calibration_reading"]
                    / MGDL_PER_MMOLL
                )
            else:
                df.loc[cal_index, "value"] = (
                    df.loc[valid_index, "payload.calibration_reading"]
                )
    else:
        n_cal_readings = 0
    return df, n_cal_readings


def get_healthkit_timezone(df):
    '''
    TODO: refactor to account for more efficient way to get embedded json
    '''
    df["payload.HKTimeZone"] = (
        expand_embedded_dict(df["payload"], "HKTimeZone")
    )
    if "timezone" not in list(df):
        if "payload.HKTimeZone" in list(df):
            hk_tz_idx = df["payload.HKTimeZone"].notnull()
            df.loc[hk_tz_idx, "deviceType"] = "healthkit"
            df.rename(columns={"payload.HKTimeZone": "timezone"}, inplace=True)

        else:
            df["timezone"] = np.nan
            df["deviceType"] = np.nan
    else:
        if "payload.HKTimeZone" in list(df):
            hk_tz_idx = df["payload.HKTimeZone"].notnull()
            df.loc[hk_tz_idx, "timezone"] = (
                df.loc[hk_tz_idx, "payload.HKTimeZone"]
            )
            df.loc[hk_tz_idx, "deviceType"] = "healthkit"
        else:
            df["timezone"] = np.nan
            df["deviceType"] = np.nan

    return df[["timezone", "deviceType"]]


def get_and_fill_timezone(df):
    '''
    this is new to deal with healthkit data
    requires that a data frame that contains payload and HKTimeZone is passed
    '''
    df = get_healthkit_timezone(df)

    df["timezone"].fillna(method='ffill', inplace=True)
    df["timezone"].fillna(method='bfill', inplace=True)

    return df["timezone"]


def make_tz_unaware(date_time):
    return date_time.replace(tzinfo=None)


def to_utc_datetime(df):
    '''
    this is new to deal with perfomance issue with the previous method
    of converting to string to datetime with pd.to_datetime()
    '''
    utc_time_tz_aware = pd.to_datetime(
        df["time"],
        format="%Y-%m-%dT%H:%M:%S",
        utc=True
    )
    utc_tz_unaware = utc_time_tz_aware.apply(make_tz_unaware)

    return utc_tz_unaware


# apply the large timezone offset correction (AKA Darin's fix)
def timezone_offset_bug_fix(df):
    '''
    this is taken from estimate-local-time.py
    TODO: add in unit testing where there is no TZP that is > 840 or < -720
    '''

    if "timezoneOffset" in list(df):

        while ((df.timezoneOffset > 840).sum() > 0):
            df.loc[df.timezoneOffset > 840, ["conversionOffset"]] = (
                df.loc[df.timezoneOffset > 840, ["conversionOffset"]]
                - (1440 * 60 * 1000)
                )

            df.loc[df.timezoneOffset > 840, ["timezoneOffset"]] = (
                df.loc[df.timezoneOffset > 840, ["timezoneOffset"]] - 1440
            )

        while ((df.timezoneOffset < -720).sum() > 0):
            df.loc[df.timezoneOffset < -720, ["conversionOffset"]] = (
                df.loc[df.timezoneOffset < -720, ["conversionOffset"]]
                + (1440 * 60 * 1000)
            )

            df.loc[df.timezoneOffset < -720, ["timezoneOffset"]] = (
                df.loc[df.timezoneOffset < -720, ["timezoneOffset"]] + 1440
            )

    return df


def get_local_time(df):

    tzo = df[['utcTime', 'inferredTimezone']].apply(
        lambda x: get_timezone_offset(*x), axis=1
    )
    local_time = df['utcTime'] + pd.to_timedelta(tzo, unit="m")

    return local_time


def round_time(
        df,
        time_interval_minutes=5,
        start_with_first_record=True,
        return_calculation_columns=False
):
    '''
    A general purpose round time function that rounds the "time"
    field to nearest <time_interval_minutes> minutes
    INPUTS:
        * a dataframe (df) or time series that contains only one time field
        that you want to round
        * time_interval_minutes (defaults to 5 minutes given that most cgms
        output every 5 minutes)
        * start_with_first_record starts the rounding with the first record
        if True, and the last record if False (defaults to True)
        * return_calculation_columns specifies whether the extra columns
        used to make calculations are returned
    refactored name(s) to meet style guide
    '''
    # if a time series is passed in, convert to dataframe
    if "Series" in get_type(df):
        df = pd.DataFrame(df)
    columns_ = list(df)
    if len(columns_) > 1:
        sys.exit(
            "Error: df should only have one time column"
        )
    else:
        df.rename(columns={columns_[0]: "t"}, inplace=True)

    df.sort_values(
        by="t",
        ascending=start_with_first_record,
        inplace=True
    )

    df.reset_index(drop=False, inplace=True)
    df.rename(columns={"index": "originalIndex"}, inplace=True)

    # calculate the time between consecutive records
    df["t_shift"] = df["t"].shift(1)
    df["timeBetweenRecords"] = round(
        (df["t"] - df["t_shift"]).dt.days*(86400/(60 * time_interval_minutes))
        + (df["t"] - df["t_shift"]).dt.seconds/(60 * time_interval_minutes)
    ) * time_interval_minutes

    # separate the data into chunks if timeBetweenRecords is greater than
    # 2 times the <time_interval_minutes> minutes so the rounding process
    # starts over
    big_gaps = list(
        df.query("abs(timeBetweenRecords) > "
                 + str(time_interval_minutes * 2)).index
    )
    big_gaps.insert(0, 0)
    big_gaps.append(len(df))

    for gap_index in range(0, len(big_gaps) - 1):
        chunk = df["t"][big_gaps[gap_index]:big_gaps[gap_index+1]]
        first_chunk = df["t"][big_gaps[gap_index]]

        # calculate the time difference between
        # each time record and the first record
        df.loc[
            big_gaps[gap_index]:big_gaps[gap_index+1],
            "minutesFromFirstRecord"
        ] = (
            (chunk - first_chunk).dt.days*(86400/60)
            + (chunk - first_chunk).dt.seconds/60
        )

        # then round to the nearest X Minutes
        # NOTE: the ".000001" ensures that mulitples of 2:30 always rounds up.
        df.loc[
            big_gaps[gap_index]:big_gaps[gap_index+1],
            "roundedMinutesFromFirstRecord"
        ] = round(
            (df.loc[
                big_gaps[gap_index]:big_gaps[gap_index+1],
                "minutesFromFirstRecord"
            ] / time_interval_minutes) + 0.000001
        ) * (time_interval_minutes)

        rounded_first_record = (
            first_chunk + pd.Timedelta("1microseconds")
        ).round(str(time_interval_minutes) + "min")

        df.loc[
            big_gaps[gap_index]:big_gaps[gap_index+1],
            "roundedTime"
        ] = rounded_first_record + pd.to_timedelta(
            df.loc[
                big_gaps[gap_index]:big_gaps[gap_index+1],
                "roundedMinutesFromFirstRecord"
            ], unit="m"
        )

    if return_calculation_columns is False:
        df.drop(
            columns=[
                "timeBetweenRecords",
                "minutesFromFirstRecord",
                "roundedMinutesFromFirstRecord"
            ], inplace=True
        )
    # sort back to the original index
    df.sort_values(by="originalIndex", inplace=True)

    return df["roundedTime"].values


def add_upload_time(df):
    '''
    this is taken from a colab notebook that is not in our github
    given that it has been refactored to account for bug where there are
    no upload records
    NOTE: this is a new fix introduced with healthkit data...we now have
    data that does not have an upload record

    '''

    if "upload" in df.type.unique():
        upload_times = pd.DataFrame(
            df[df.type == "upload"].groupby("uploadId")["utcTime"].max()
        )
    else:
        upload_times = pd.DataFrame(columns=["utcTime"])

    unique_uploadIds = set(df["uploadId"].unique())
    unique_uploadRecords = set(
        df.loc[df["type"] == "upload", "uploadId"].unique()
    )
    uploadIds_missing_uploadRecords = unique_uploadIds - unique_uploadRecords

    for upId in uploadIds_missing_uploadRecords:
        last_upload_time = df.loc[df["uploadId"] == upId, "utcTime"].max()
        upload_times.loc[upId, "utcTime"] = last_upload_time

    upload_times.reset_index(inplace=True)
    upload_times.rename(
        columns={"utcTime": "uploadTime",
                 "index": "uploadId"},
        inplace=True
    )

    df = pd.merge(df, upload_times, how='left', on='uploadId')

    return df["uploadTime"].values


def remove_invalid_cgm_values(df):

    nBefore = len(df)
    # remove values < 38 and > 402 mg/dL
    df = df.drop(df[((df.type == "cbg") &
                     (df["mg/dL"] < 38))].index)
    df = df.drop(df[((df.type == "cbg") &
                     (df["mg/dL"] > 402))].index)
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
        dfNotNull, nDuplicatesRemoved = (
            removeDuplicates(dfNotNull, [timeCriterion, "value"])
        )
        df = pd.concat([dfIsNull, dfNotNull])
        df.sort_values(by=[timeCriterion, "uploadTime"],
                       ascending=[False, False],
                       inplace=True)
    else:
        nDuplicatesRemoved = 0

    return df, nDuplicatesRemoved


# get rid of spike data
def remove_spike_data(df):
    nBefore = len(df)
    spike_locations = [
        "origin.payload.device.name",
        "origin.payload.device.manufacturer",
        "origin.payload.sourceRevision.source.name",
    ]
    for spike_loc in spike_locations:

        df[spike_loc] = get_embedded_field(df["origin"], spike_loc)
        spike_idx = df.loc[
            df[spike_loc].notnull(),
            spike_loc
        ].str.lower().str.contains("spike")
        df.drop(df.iloc[np.where(spike_idx)[0]].index, inplace=True)
    nRemoved = nBefore - len(df)

    return df, nRemoved


# %% ESTIMATE LOCAL TIME FUNCTIONS
def create_contiguous_day_series(df):
    first_day = df["date"].min()
    last_day = df["date"].max()
    rng = pd.date_range(first_day, last_day).date
    contiguousDaySeries = \
        pd.DataFrame(rng, columns=["date"]).sort_values(
                "date", ascending=False).reset_index(drop=True)

    return contiguousDaySeries


def add_device_type(df):
    col_headings = list(df)
    if "deviceType" not in col_headings:
        df["deviceType"] = np.nan
    if "deviceTags" in col_headings:
        # first make sure deviceTag is in string format
        df["deviceTags"] = df.deviceTags.astype(str)
        # filter by type not null device tags
        ud = df[df["deviceTags"].notnull()].copy()
        # define a device type (e.g., pump, cgm, or healthkit)
        ud.loc[
            ((ud["deviceTags"].str.contains("pump"))
             & (ud["deviceType"].isnull())),
            ["deviceType"]
        ] = "pump"

        # define a device type (e.g., cgm)
        ud.loc[
            ((ud["deviceTags"].str.contains("cgm"))
             & (ud["deviceType"].isnull())),
            ["deviceType"]
        ] = "cgm"

        return ud["deviceType"]
    else:
        return np.nan


def get_timezone_offset(currentDate, currentTimezone):

    tz = pytz.timezone(currentTimezone)
    # here we add 1 day to the current date to account for changes to/from DST
    tzoNum = int(
        tz.localize(currentDate + dt.timedelta(days=1)).strftime("%z")
    )
    tzoHours = np.floor(tzoNum / 100)
    tzoMinutes = round((tzoNum / 100 - tzoHours) * 100, 0)
    tzoSign = np.sign(tzoHours)
    tzo = int((tzoHours * 60) + (tzoMinutes * tzoSign))

    return tzo


def add_device_day_series(df, dfContDays, deviceTypeName):
    if len(df) > 0:
        dfDayGroups = df.groupby("date")
        if "timezoneOffset" in df:
            dfDaySeries = pd.DataFrame(dfDayGroups["timezoneOffset"].median())
        else:
            dfDaySeries = pd.DataFrame(columns=["timezoneOffset"])

        if "upload" in deviceTypeName:
            if "timezone" in df:
                if dfDayGroups.timezone.count().max() > 0:
                    dfDaySeries["timezone"] = (
                        dfDayGroups.timezone.describe()["top"]
                    )
                    # get the timezone offset for the timezone
                    for i in dfDaySeries.index:
                        if pd.notnull(dfDaySeries.loc[i, "timezone"]):
                            tzo = get_timezone_offset(
                                    pd.to_datetime(i),
                                    dfDaySeries.loc[i, "timezone"])
                            dfDaySeries.loc[i, ["timezoneOffset"]] = tzo
                    if "timeProcessing" in dfDaySeries:
                        dfDaySeries["timeProcessing"] = \
                            dfDayGroups.timeProcessing.describe()["top"]
                    else:
                        dfDaySeries["timeProcessing"] = np.nan

        dfDaySeries = dfDaySeries.add_prefix(deviceTypeName + "."). \
            rename(columns={deviceTypeName + ".date": "date"})

        dfContDays = pd.merge(dfContDays, dfDaySeries.reset_index(),
                              on="date", how="left")

    else:
        dfContDays[deviceTypeName + ".timezoneOffset"] = np.nan

    return dfContDays


def impute_upload_records(df, contDays, deviceTypeName):
    daySeries = \
        add_device_day_series(df, contDays, deviceTypeName)

    if ((len(df) > 0) & (deviceTypeName + ".timezone" in daySeries)):
        for i in daySeries.index[1:]:
            if pd.isnull(daySeries[deviceTypeName + ".timezone"][i]):
                daySeries.loc[i, [deviceTypeName + ".timezone"]] = (
                    daySeries.loc[i-1, deviceTypeName + ".timezone"]
                )
            if pd.notnull(daySeries[deviceTypeName + ".timezone"][i]):
                tz = daySeries.loc[i, deviceTypeName + ".timezone"]
                tzo = get_timezone_offset(
                    pd.to_datetime(daySeries.loc[i, "date"]),
                    tz
                )
                daySeries.loc[i, deviceTypeName + ".timezoneOffset"] = tzo

            if pd.notnull(daySeries[deviceTypeName + ".timeProcessing"][i-1]):
                daySeries.loc[i, deviceTypeName + ".timeProcessing"] = \
                    daySeries.loc[i-1, deviceTypeName + ".timeProcessing"]

    else:
        daySeries[deviceTypeName + ".timezone"] = np.nan
        daySeries[deviceTypeName + ".timeProcessing"] = np.nan

    return daySeries


def add_home_timezone(df, contDays):

    if "timezone" in df:
        homeTimezone = df["timezone"].describe()["top"]
        tzo = contDays.date.apply(
                lambda x: get_timezone_offset(pd.to_datetime(x), homeTimezone))

        contDays["home.imputed.timezoneOffset"] = tzo
        contDays["home.imputed.timezone"] = homeTimezone

    else:
        contDays["home.imputed.timezoneOffset"] = np.nan
        contDays["home.imputed.timezone"] = np.nan
    contDays["home.imputed.timeProcessing"] = np.nan

    return contDays


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
    sIndices = cDF[((cDF["est.type"] == "DEVICE") &
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


def getRangeOfTZOsForTimezone(tz):
    minMaxTzo = [getTimezoneOffset(pd.to_datetime("1/1/2017"), tz),
                 getTimezoneOffset(pd.to_datetime("5/1/2017"), tz)]

    rangeOfTzo = np.arange(int(min(minMaxTzo)), int(max(minMaxTzo))+1, 15)

    return rangeOfTzo


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
        dstIndex = df[(df.date > (d + dt.timedelta(days=-2))) &
                      (df.date < (d + dt.timedelta(days=2)))].index
        for dIdx in dstIndex:
            if pd.notnull(df.loc[dIdx, "est.timezone"]):
                tz = pytz.timezone(df.loc[dIdx, "est.timezone"])
                tzRange = getRangeOfTZOsForTimezone(str(tz))
                minHoursToLocal = min(tzRange)/60
                tzoNum = int(tz.localize(df.loc[dIdx, "utcTime"] +
                             dt.timedelta(hours=minHoursToLocal)).strftime("%z"))
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

    return df["est.localTime"].values


def isDSTChangeDay(currentDate, currentTimezone):
    tzoCurrentDay = getTimezoneOffset(pd.to_datetime(currentDate),
                                      currentTimezone)
    tzoPreviousDay = getTimezoneOffset(pd.to_datetime(currentDate) +
                                       dt.timedelta(days=-1), currentTimezone)

    return (tzoCurrentDay != tzoPreviousDay)


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


def addAnnotation(df, idx, annotationMessage):
    if pd.notnull(df.loc[idx, "est.annotations"]):
        df.loc[idx, ["est.annotations"]] = df.loc[idx, "est.annotations"] + \
            ", " + annotationMessage
    else:
        df.loc[idx, ["est.annotations"]] = annotationMessage

    return df


def getTimezoneOffset(currentDate, currentTimezone):

    tz = pytz.timezone(currentTimezone)
    # here we add 1 day to the current date to account for changes to/from DST
    tzoNum = int(tz.localize(currentDate + dt.timedelta(days=1)).strftime("%z"))
    tzoHours = np.floor(tzoNum / 100)
    tzoMinutes = round((tzoNum / 100 - tzoHours) * 100, 0)
    tzoSign = np.sign(tzoHours)
    tzo = int((tzoHours * 60) + (tzoMinutes * tzoSign))

    return tzo


def estimate_local_time(df):
    df["date"] = df["utcTime"].dt.date  # TODO: change this to utcDate later
    contiguous_days = create_contiguous_day_series(df)

    df["deviceType"] = add_device_type(df)
    cDays = add_device_day_series(df, contiguous_days, "upload")

    # create day series for cgm df
    if "timezoneOffset" not in list(df):
        df["timezoneOffset"] = np.nan

    cgmdf = df[(df["type"] == "cbg") & (df["timezoneOffset"].notnull())].copy()
    cDays = add_device_day_series(cgmdf, cDays, "cgm")

    # create day series for pump df
    pumpdf = df[(df.type == "bolus") & (df.timezoneOffset.notnull())].copy()
    cDays = add_device_day_series(pumpdf, cDays, "pump")

    # interpolate between upload records of the same deviceType, and create a
    # day series for interpolated pump, non-hk-cgm, and healthkit uploads
    for deviceType in ["pump", "cgm", "healthkit"]:
        tempUploaddf = df[df["deviceType"] == deviceType].copy()
        cDays = impute_upload_records(
            tempUploaddf, cDays, deviceType + ".upload.imputed"
        )

    # add a home timezone that also accounts for daylight savings time changes
    cDays = add_home_timezone(df, cDays)

    # 1. USE UPLOAD RECORDS TO ESTIMATE TZ AND TZO
    cDays = estimateTzAndTzoWithUploadRecords(cDays)

    # 2. USE DEVICE TZOs TO ESTIMATE TZO AND TZ (IF POSSIBLE)
    # estimates can be made from pump and cgm df that have a TZO
    # NOTE: the healthkit and dexcom-api cgm df are excluded
    cDays = estimateTzAndTzoWithDeviceRecords(cDays)

    # 3. impute, infer, or interpolate gaps in the estimated tzo and tz
    cDays = imputeTzAndTzo(cDays)

    # 4. APPLY LOCAL TIME ESTIMATES TO ALL df
    local_time = applyLocalTimeEstimates(df, cDays)

    return local_time, cDays


# %% GET DATA FROM API
'''
get metadata and data for a donor that has shared with bigdata
NOTE: functions assume you have an .env with bigdata account credentials
'''

userid = "0d4524bc11"
donor_group = "bigdata"

donor_metadata, _ = get_shared_metadata(
    donor_group=donor_group,
    userid_of_shared_user=userid  # TODO: this should be refactored in several places to be userid
)
data, _ = get_data(
    donor_group=donor_group,
    userid=userid,
    weeks_of_data=52*10
)


# %% CREATE META DATAFRAME (metadata)
'''
this is useful for keeping track of the type and amount of cleaning done
'''
metadata = pd.DataFrame(index=[userid])


# %% HASH USER ID
hashid = hash_userid(userid, os.environ['BIGDATA_SALT'])
data["userid"] = userid
data["hashid"] = hashid


# %% CLEAN DATA
data_fields = list(data)
# remove negative durations
if "duration" in data_fields:
    data["duration"], n_negative_durations = (
        remove_negative_durations(data[["duration"]].copy())
    )
else:
    n_negative_durations = np.nan
metadata["nNegativeDurations"] = n_negative_durations

# Tslim calibration bug fix
data, n_cal_readings = tslim_calibration_fix(data.copy())
metadata["nTandemAndPayloadCalReadings"] = n_cal_readings

# fix large timzoneOffset bug in utcbootstrapping
data = timezone_offset_bug_fix(data.copy())

# add healthkit timezome information
data[["timezone", "deviceType"]] = get_healthkit_timezone(data.copy())


# %% TIME RELATED ITEMS
data["utcTime"] = to_utc_datetime(data[["time"]].copy())

# add upload time to the data, which is needed for:
# getting rid of duplicates and useful for getting local time
data["uploadTime"] = add_upload_time(data[
    ["type", "uploadId", "utcTime"]
].copy())

# estimate local time (refactor of estimate-local-time.py)
data["localTime"], local_time_metadata = estimate_local_time(data.copy())

# round all data to the nearest 5 minutes
data["roundedLocalTime"] = round_time(
    data["localTime"].copy(),
    time_interval_minutes=5,
    start_with_first_record=True,
    return_calculation_columns=False
)


# %% TIME CATEGORIES
# AGE, & YLW
bDate = pd.to_datetime(donor_metadata["birthday"].values[0][0:7])
dDate = pd.to_datetime(donor_metadata["diagnosisDate"].values[0][0:7])
data["age"] = np.floor((data["roundedLocalTime"] - bDate).dt.days/365.25)
data["ylw"] = np.floor((data["roundedLocalTime"] - dDate).dt.days/365.25)

# hour of the day
data["hour"] = data["roundedLocalTime"].dt.hour

# add the day of the localTime that starts at 12am
data["day12AM"] = data["roundedLocalTime"].dt.date
# NOTE: for day of week Monday = 0 and Sunday = 6
data["dayofweek12AM"] = data["roundedLocalTime"].dt.dayofweek
data["weekend12AM"] = data["dayofweek12AM"] > 4

# day that starts at 6am
data["6amTime"] = data["roundedLocalTime"] - pd.Timedelta(6, unit="hours")
data["day6AM"] = data["6amTime"].dt.date
data["dayofweek6AM"] = data["6amTime"].dt.dayofweek
data["weekend6AM"] = data["dayofweek6AM"] > 4


# %% GROUP DATA BY TYPE
# first sort by upload time (used when removing dumplicates)
data.sort_values("uploadTime", ascending=False, inplace=True)
groups = data.groupby(by="type")


# %% CGM DATA
# filter by cgm
cgm = groups.get_group("cbg").dropna(axis=1, how="all")

# calculate cgm in mg/dL
cgm["mg/dL"] = round(cgm["value"] * MGDL_PER_MMOLL)

# get rid of spike data
cgm, nSpike = remove_spike_data(cgm)
metadata["nSpike"] = nSpike

# get rid of cgm values too low/high (< 38 & > 402 mg/dL)
cgm, nInvalidCgmValues = remove_invalid_cgm_values(cgm)
metadata["nInvalidCgmValues"] = nInvalidCgmValues

# get rid of duplicates that have the same ["deviceTime", "value"]
cgm, n_cgm_dups_removed = (removeCgmDuplicates(cgm, "deviceTime"))
metadata["nCgmDuplicatesRemovedDeviceTime"] = n_cgm_dups_removed

# get rid of duplicates that have the same ["time", "value"]
cgm, n_cgm_dups_removed = removeCgmDuplicates(cgm, "time")
metadata["nCgmDuplicatesRemovedUtcTime"] = n_cgm_dups_removed

# get rid of duplicates that have the same "roundedTime"
cgm, n_cgm_dups_removed = removeDuplicates(cgm, "roundedLocalTime")
metadata["nCgmDuplicatesRemovedRoundedTime"] = n_cgm_dups_removed


# %% GET CGM STATS
# create a contiguous 5 minute time series
first_day = cgm["roundedLocalTime"].min()
last_day = cgm["roundedLocalTime"].max()
rng = pd.date_range(first_day, last_day, freq="5min")
contiguous_data = (
    pd.DataFrame(rng, columns=["roundedLocalTime"]).sort_values(
        "roundedLocalTime", ascending=False
    ).reset_index(drop=True)
)

# merge with cgm data
cgm_series = pd.merge(
    contiguous_data,
    cgm,
    on="roundedLocalTime",
    how="left"
)

#cgm_series["hourly.mean"] = cgm_series["mg/dL"].rolling(12).mean()
