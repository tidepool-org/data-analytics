#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
calculate cgm statsistics for a single tidepool (donor) dataset
'''


# %% REQUIRED LIBRARIES
import os
import sys
import sys
import hashlib
import pytz
import numpy as np
import pandas as pd
import datetime as dt
import pdb

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


def expand_embedded_dict(df, field, key_):
    '''
    this is new, should be refactored for speed as the current process
    creates a dataframe of all of keys instead of just the key of interest
    '''
    if field in list(df):
        notnull_idx = df[field].notnull()
        temp_df = pd.DataFrame(df.loc[notnull_idx, field].tolist())  # TODO: this can be sped up by only getting the field key of interest
        if key_ in list(temp_df):
            df[field + "." + key_] = temp_df[key_]
    return df


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
    df = expand_embedded_dict(df, "payload", "calibration_reading")

    if "payload.calibration_reading" in list(df):

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


def get_and_fill_timezone(df):
    '''
    this is new to deal with healthkit data
    requires that a data frame that contains payload and HKTimeZone is passed
    '''
    df = expand_embedded_dict(df, "payload", "HKTimeZone")
    if "timezone" not in list(df):
        if "payload.HKTimeZone" in list(df):
            df.rename(columns={"payload.HKTimeZone": "timezone"}, inplace=True)
        else:
            df["timezone"] = np.nan
    else:
        if "payload.HKTimeZone" in list(df):
            hk_tz_idx = df["payload.HKTimeZone"].notnull()
            df.loc[hk_tz_idx, "timezone"] = (
                df.loc[hk_tz_idx, "payload.HKTimeZone"]
            )

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


def get_timezone_offset(currentDate, currentTimezone):

    # edge case for 'US/Pacific-New'
    if currentTimezone == 'US/Pacific-New':
        currentTimezone = 'US/Pacific'

    tz = pytz.timezone(currentTimezone)

    tzoNum = int(
        tz.localize(currentDate + dt.timedelta(days=1)).strftime("%z")
    )
    tzoHours = np.floor(tzoNum / 100)
    tzoMinutes = round((tzoNum / 100 - tzoHours) * 100, 0)
    tzoSign = np.sign(tzoHours)
    tzo = int((tzoHours * 60) + (tzoMinutes * tzoSign))

    return tzo


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
    weeks_of_data=4
    )


# %% CREATE META DATAFRAME (metadata)
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
data, n_cal_readings = tslim_calibration_fix(data)
metadata["nTandemAndPayloadCalReadings"] = n_cal_readings


# %% TIME RELATED ITEMS
data["utcTime"] = to_utc_datetime(data[["time"]].copy())
if "timezone" not in list(data):
    data["timezone"] = np.nan
data["inferredTimezone"] = get_and_fill_timezone(
    data[["timezone", "payload"]].copy()
)
# estimate local time (simple method)
# TODO: this really needs to be sped up
data["localTime"] = get_local_time(
    data[['utcTime', 'inferredTimezone']].copy()
)

# round all data to the nearest 5 minutes
data["roundedTime"] = round_time(
    data["localTime"].copy(),
    time_interval_minutes=5,
    start_with_first_record=True,
    return_calculation_columns=False
)





#data["day"] = pd.DatetimeIndex(data["localTime"]).date
#
## round to the nearest 5 minutes
## TODO: once roundTime is pushed to tidals repository then this line can be replaced
## with td.clean.round_time
#data = round_time(data, time_interval_minutes=5, time_field="time",
#                  rounded_field_name="roundedTime", start_with_first_record=True,
#                  verbose=False)
#
#data["roundedLocalTime"] = data["roundedTime"] + pd.to_timedelta(data["tzo"], unit="m")
#data.sort_values("uploadTime", ascending=False, inplace=True)
#
## AGE, & YLW
#data["age"] = np.floor((data["localTime"] - bDate).dt.days/365.25).astype(int)
#data["ylw"] = np.floor((data["localTime"] - dDate).dt.days/365.25).astype(int)


# %% CGM DATA

#def removeInvalidCgmValues(df):
#
#    nBefore = len(df)
#    # remove values < 38 and > 402 mg/dL
#    df = df.drop(df[((df.type == "cbg") &
#                     (df.value < 2.109284236597303))].index)
#    df = df.drop(df[((df.type == "cbg") &
#                     (df.value > 22.314006924003046))].index)
#    nRemoved = nBefore - len(df)
#
#    return df, nRemoved

# get rid of cgm values too low/high (< 38 & > 402 mg/dL)
#data, nInvalidCgmValues = removeInvalidCgmValues(data)
#metadata["nInvalidCgmValues"] = nInvalidCgmValues

