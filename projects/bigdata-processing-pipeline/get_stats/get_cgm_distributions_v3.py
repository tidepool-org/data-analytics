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
import glob
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
from get_donor_data.get_single_tidepool_dataset_json import make_folder_if_doesnt_exist

# %% CONSTANTS
MGDL_PER_MMOLL = 18.01559


# %% FUNCTIONS
'''
the functions that are called in this script,
which includes notes of where the functions came from,
and whether they were refactored
'''


def get_episodes(df, episode_criterion, min_duration):

    # put consecutive data that matches in groups
    df["tempGroups"] = ((
        df[episode_criterion] != df[episode_criterion].shift()
    ).cumsum())

    df["episodeId"] = (
        df["tempGroups"] * df[episode_criterion]
    )

    # group by the episode groups
    episode_groups = df.groupby("episodeId")
    episodes = episode_groups["roundedUtcTime"].count().reset_index()
    episodes["duration"] = episodes["roundedUtcTime"] * 5
    episodes.rename(columns={"roundedUtcTime": "episodeCounts"}, inplace=True)

    df = pd.merge(df, episodes, on="episodeId", how="left")
    df["episodeDuration"] = (
        df["duration"] * df[episode_criterion]
    )

    # get rolling stats on episodes
    df["isEpisode"] = (
        df["episodeDuration"] >= min_duration
    )

    # get the hypo episode starts so we only count each episode once
    df["episodeStart"] = (
        (df[episode_criterion])
        & (~df[episode_criterion].shift(1).fillna(False))
        & (df["hasCgm"])
        & (df["hasCgm"].shift(1))
    )

    df = df[[
        "isEpisode", "episodeStart",
        "episodeId", "episodeDuration"
    ]].add_prefix("episode." + episode_criterion + ".")

    return df


def get_slope(y):
    if "array" not in type(y).__name__:
        raise TypeError('Expecting a numpy array')

    count_ = len(y)

    x = np.arange(start=0, stop=count_*5, step=5)

    sum_x = x.sum()
    sum_y = y.sum()
    sum_xy = (x * y).sum()
    sum_x_squared = (x * x).sum()

    slope = (
        ((count_ * sum_xy) - (sum_x * sum_y))
        / ((count_ * sum_x_squared) - (sum_x * sum_x))
    )

    return slope


def expand_entire_dict(ts):
    if "Series" not in type(ts).__name__:
        raise TypeError('Expecting a pandas time series object')
    notnull_idx = ts.index[ts.notnull()]
    temp_df = pd.DataFrame(
        ts[notnull_idx].tolist(),
        index=notnull_idx
    )

    return temp_df


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
    temp_df = expand_entire_dict(ts)
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


def add_upload_info_to_cgm_records(groups, df):
    upload_locations = [
        "upload.uploadId",
        "upload.deviceManufacturers",
        "upload.deviceModel",
        "upload.deviceSerialNumber",
        "upload.deviceTags"
    ]

    if "upload" in groups["type"].unique():
        upload = groups.get_group("upload").dropna(axis=1, how="all").add_prefix("upload.")
        df = pd.merge(
            left=df,
            right=upload[list(set(upload_locations) & set(list(upload)))],
            left_on="uploadId",
            right_on="upload.uploadId",
            how="left"
        )

    return df


def expand_heathkit_cgm_fields(df):
    # TODO: refactor the code/function that originally grabs
    # these fields, so we are only doing it once, and so
    # we don't have to drop the columns for the code below to work.
    drop_columns = [
        'origin.payload.device.name',
        'origin.payload.device.manufacturer',
        'origin.payload.sourceRevision.source.name'
    ]
    for drop_col in drop_columns:
        if drop_col in list(df):
            df.drop(columns=[drop_col], inplace=True)

    healthkit_locations = [
        "origin",
        "origin.payload",
        "origin.payload.device",
        "origin.payload.sourceRevision",
        "origin.payload.sourceRevision.source",
        "payload",
    ]

    for hk_loc in healthkit_locations:
        if hk_loc in list(df):
            temp_df = (
                expand_entire_dict(df[hk_loc].copy()).add_prefix(hk_loc + ".")
            )
            df = pd.concat([df, temp_df], axis=1)

    return df


def get_dexcom_cgm_model(df):
    # add cgm model

    dexcom_model_locations = [
        "deviceId",
        "deviceManufacturers",
        "upload.deviceManufacturers",
        "deviceModel",
        "upload.deviceModel",
        "deviceSerialNumber",
        "upload.deviceSerialNumber",
        "origin.payload.sourceRevision.source.name",
        "payload.transmitterGeneration",
        "payload.HKMetadataKeySyncIdentifier",
        "payload.transmitterId",
    ]

    for model_location in dexcom_model_locations:
        # only check if model has NOT been determined, or if it is G5_G6
        m_idx = (
            (df["cgmModel"].isnull())
            | (df["cgmModel"].astype(str).str.contains("G5_G6"))
        )

        # get index that matches model
        if ((model_location in list(df)) & (m_idx.sum() > 0)):
            str_list = df[model_location].astype(str).str

            # G4
            g4_idx = str_list.contains("G4", case=False, na=False)
            df.loc[g4_idx, "cgmModel"] = "G4"
            df.loc[g4_idx, "cgmModelSensedFrom"] = model_location

            # G5
            g5_idx = str_list.contains("G5", case=False, na=False)
            df.loc[g5_idx, "cgmModel"] = "G5"
            df.loc[g5_idx, "cgmModelSensedFrom"] = model_location

            # G6
            g6_idx = str_list.contains("G6", case=False, na=False)
            df.loc[g6_idx, "cgmModel"] = "G6"
            df.loc[g6_idx, "cgmModelSensedFrom"] = model_location

            # edge case of g5 and g6
            g5_g6_idx = (g5_idx & g6_idx)
            df.loc[g5_g6_idx, "cgmModel"] = "G5_G6"
            df.loc[g5_g6_idx, "cgmModelSensedFrom"] = model_location

            # case of "transmitterId"
            if (
                ("transmitterId" in model_location)
                | ("payload.HKMetadataKeySyncIdentifier" in model_location)
            ):
                # if length of string is 5, then it is likely a G4 sensor
                length5_idx = str_list.len() == 5
                df.loc[length5_idx, "cgmModel"] = "G4"
                df.loc[length5_idx, "cgmModelSensedFrom"] = model_location

                # if length of string > 5  then might be G5 or G6
                length_gt5_idx = str_list.len() > 5

                # if sensor stats with 4 then likely G5
                starts4_idx = str_list.startswith("4")
                df.loc[(length_gt5_idx & starts4_idx), "cgmModel"] = "G5"
                df.loc[(length_gt5_idx & starts4_idx), "cgmModelSensedFrom"] = model_location

                # if sensor stats with 2 or 8 then likely G6
                starts2_6_idx = (
                    (str_list.startswith("2")) | (str_list.startswith("8"))
                )
                df.loc[(length_gt5_idx & starts2_6_idx), "cgmModel"] = "G6"
                df.loc[(length_gt5_idx & starts2_6_idx), "cgmModelSensedFrom"] = model_location

    return df[["cgmModel", "cgmModelSensedFrom"]]


def get_non_dexcom_cgm_model(df):
    # non-dexcom cgm model query
    model_locations = ["deviceId"]

    # model types (NOTE: for medtronic getting pump type not cgm)
    models_670G = "MMT-158|MMT-178"
    models_640G = "MMT-1511|MMT-1512|MMT-1711|MMT-1712"
    models_630G = "MMT-1514|MMT-1515|MMT-1714|MMT-1715"
    models_530G = (
        "530G|MedT-551|MedT-751|MedT-554|MedT-754|Veo - 554|Veo - 754"
    )
    models_523_723 = "MedT-523|MedT-723|Revel - 523|Revel - 723"  # 523/723
    models_libre = "AbbottFreeStyleLibre"
    models_animas = "IR1295"
    # NOTE: the tandem G4 will first be written as G5_G6,
    # but the logic should overwrite back to G4
    models_tandem_G5_G6 = "tandem"
    models_tandem_G4 = "4628003|5448003"

    non_dex_models = [
        models_670G, models_640G, models_630G, models_530G, models_523_723,
        models_libre, models_animas, models_tandem_G5_G6, models_tandem_G4
    ]

    non_dex_model_names = [
        "670G", "640G", "630G", "530G", "523_723",
        "LIBRE", "G4", "G5_G6", "G4"
    ]

    for model_location in model_locations:
        # only check if model has NOT been determined, or if it is G5_G6
        m_idx = (
            (df["cgmModel"].isnull())
            | (df["cgmModel"].astype(str).str.contains("G5_G6"))
        )

        # get index that matches model
        if ((model_location in list(df)) & (m_idx.sum() > 0)):
            str_list = df[model_location].astype(str).str

            for non_dex_model, model_name in zip(
                non_dex_models, non_dex_model_names
            ):

                model_idx = str_list.contains(non_dex_model, na=False)
                df.loc[model_idx, "cgmModel"] = model_name
                df.loc[model_idx, "cgmModelSensedFrom"] = model_location

    return df[["cgmModel", "cgmModelSensedFrom"]]


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
    TODO: I think that durations are coming in as floats too, so we need
    to refactor to account for that.
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
    if "payload" in list(df):
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
    else:
        n_cal_readings = 0
    return df, n_cal_readings


def replace_smoothed_cgm_values(df):

    if 'payload.realTimeValue' in list(df):
        raw_val_idx = df['payload.realTimeValue'].notnull()
        n_replaced = raw_val_idx.sum()
        df.loc[raw_val_idx, "mg/dL"] = (
            df.loc[raw_val_idx, "payload.realTimeValue"]
        )
    else:
        n_replaced = np.nan

    raw_values = df["mg/dL"]

    return raw_values, n_replaced


def get_healthkit_timezone(df):
    '''
    TODO: refactor to account for more efficient way to get embedded json
    '''
    if "payload" in list(df):
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
    df = df.drop(df[((df.type == "cbg") & (df["mg/dL"] < 38))].index)
    df = df.drop(df[((df.type == "cbg") & (df["mg/dL"] > 402))].index)
    nRemoved = nBefore - len(df)

    return df, nRemoved


def removeDuplicates(df, criteriaDF):
    nBefore = len(df)
    df = df.loc[~(df[criteriaDF].duplicated())]
    df = df.reset_index(drop=True)
    nDuplicatesRemoved = nBefore - len(df)

    return df, nDuplicatesRemoved


def removeCgmDuplicates(df, timeCriterion, valueCriterion="value"):
    if timeCriterion in df:
        df.sort_values(by=[timeCriterion, "uploadTime"],
                       ascending=[False, False],
                       inplace=True)
        dfIsNull = df[df[timeCriterion].isnull()]
        dfNotNull = df[df[timeCriterion].notnull()]
        dfNotNull, nDuplicatesRemoved = (
            removeDuplicates(dfNotNull, [timeCriterion, valueCriterion])
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
    if "origin" in list(df):
        nBefore = len(df)
        spike_locations = [
            "origin.payload.device.name",
            "origin.payload.device.manufacturer",
            "origin.payload.sourceRevision.source.name",
        ]
        for spike_loc in spike_locations:
            df[spike_loc] = get_embedded_field(df["origin"], spike_loc)
            notnull_idx = df[spike_loc].notnull()
            df_notnull = df[notnull_idx]
            is_spike = df_notnull[spike_loc].astype(str).str.lower().str.contains("spike")
            spike_idx = df_notnull[is_spike].index
            df.drop(spike_idx, inplace=True)

        nRemoved = nBefore - len(df)

    else:
        nRemoved = np.nan

    return df, nRemoved


# %% ESTIMATE LOCAL TIME FUNCTIONS
def convert_deprecated_timezone_to_alias(df, tzAlias):
    if "timezone" in df:
        uniqueTimezones = df.timezone.unique()
        uniqueTimezones = uniqueTimezones[pd.notnull(df.timezone.unique())]

        for uniqueTimezone in uniqueTimezones:
            alias = tzAlias.loc[tzAlias.tz.str.endswith(uniqueTimezone),
                                ["alias"]].values
            if len(alias) == 1:
                df.loc[df.timezone == uniqueTimezone, ["timezone"]] = alias

    return df


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
            dfDaySeries.index.name = "date"

        if "upload" in deviceTypeName:
            if (("timezone" in df) & (df["timezone"].notnull().sum() > 0)):
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

    if (("timezone" in df) & (df["timezone"].notnull().sum()> 0)):
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


# %% GET DATA FROM JSON FILE
data_path = os.path.join("..", "data")
all_donor_metadata = pd.read_csv(
    os.path.join(
        data_path,
        "PHI-2019-07-17-donor-data",
        "PHI-2019-07-17-donor-metadata.csv"),
    low_memory=False
)

# glob through the json files that are available
all_files = glob.glob(
    os.path.join(
        data_path,
        "dremio",
        "**",
        "*.json"
    ),
    recursive=True
)

output_metadata = os.path.join(
    data_path,
    "PHI-2019-07-17-donor-data",
    "PHI-2019-07-17-cgm-metadata"
)
output_distribution = os.path.join(
    data_path,
    "PHI-2019-07-17-donor-data",
    "PHI-2019-07-17-cgm-distributions"
)
debug_duplicates = os.path.join(
    data_path,
    "PHI-2019-07-17-donor-data",
    "PHI-2019-07-17-debug-cgm-duplicates"
)
output_stats = os.path.join(
    data_path,
    "PHI-2019-07-17-donor-data",
    "PHI-2019-07-17-cgm-stats"
)


make_folder_if_doesnt_exist(
    [output_metadata, output_distribution, debug_duplicates, output_stats]
)


# %% START OF CODE
timezone_aliases = pd.read_csv(
    "wikipedia-timezone-aliases-2018-04-28.csv",
    low_memory=False
)

donor_metadata_columns = [
    'userid',
    'diagnosisType',
    'diagnosisDate',
    'biologicalSex',
    'birthday',
    'targetTimezone',
    'targetDevices',
    'isOtherPerson',
]


## %% load test data on my computer
## TODO: if data comes in as a .csv, the embedded json fields
## get saved as a string and need to be unwrapped before those fields
## can be expanded. IN OTHER WORDS: this code only works with .json data
for d_idx in [0]:
    userid = "0d4524bc11"
    data = pd.read_json(os.path.join(
            "..", "data", "dremio", userid, "PHI-{}.json".format(userid)
    ))

## %%
#for d_idx in range(0, len(all_files)):
#    data = pd.read_json(all_files[d_idx])
#    userid = all_files[d_idx][-15:-5]
    metadata = all_donor_metadata.loc[
        all_donor_metadata["userid"] == userid,
        donor_metadata_columns
    ]
    print("\n", "starting", userid)

    #  HASH USER ID
    hashid = hash_userid(userid, os.environ['BIGDATA_SALT'])
    data["userid"] = userid
    data["hashid"] = hashid
    metadata["hashid"] = hashid

    #  CLEAN DATA
    data_fields = list(data)

    # NOTE: moving remove negative durations to type specific cleaning
    # TODO: ask backend to change "duration" to only include one object type

    # Tslim calibration bug fix
    data, n_cal_readings = tslim_calibration_fix(data.copy())
    metadata["nTandemAndPayloadCalReadings"] = n_cal_readings

    # fix large timzoneOffset bug in utcbootstrapping
    data = timezone_offset_bug_fix(data.copy())

    # add healthkit timezome information
    # TODO: refactor this function to only require fields that might have hk tz
    data[["timezone", "deviceType"]] = get_healthkit_timezone(data.copy())

    # convert deprecated timezones to their aliases
    data = convert_deprecated_timezone_to_alias(data, timezone_aliases)

    #  TIME RELATED ITEMS
    data["utcTime"] = to_utc_datetime(data[["time"]].copy())

    # add upload time to the data, which is needed for:
    # getting rid of duplicates and useful for getting local time

    data["uploadTime"] = (
        add_upload_time(data[["type", "uploadId", "utcTime"]].copy())
    )

#    # estimate local time (refactor of estimate-local-time.py)
#    data["localTime"], local_time_metadata = estimate_local_time(data.copy())
#
# TODO: fix this issue with estimate local time
#    '''
#    //anaconda3/envs/tbddp/lib/python3.7/site-packages/pandas/core/ops.py:1649
#    FutureWarning: elementwise comparison failed; returning scalar instead,
#    but in the future will perform elementwise comparison result = method(y)
#    '''

    # round all data to the nearest 5 minutes
    data["roundedUtcTime"] = round_time(
        data["utcTime"].copy(),
        time_interval_minutes=5,
        start_with_first_record=True,
        return_calculation_columns=False
    )

    #  TIME CATEGORIES
    data["date"] = data["roundedUtcTime"].dt.date

    # AGE, & YLW
    # TODO: make this a function
    if metadata["birthday"].values[0] is not np.nan:
        bDate = pd.to_datetime(metadata["birthday"].values[0][0:7])
        data["age"] = np.floor((data["roundedUtcTime"] - bDate).dt.days/365.25)
    else:
        data["age"] = np.nan

    if metadata["diagnosisDate"].values[0] is not np.nan:
        dDate = pd.to_datetime(metadata["diagnosisDate"].values[0][0:7])
        data["ylw"] = np.floor((data["roundedUtcTime"] - dDate).dt.days/365.25)
    else:
        data["ylw"] = np.nan

    #  GROUP DATA BY TYPE
    # first sort by upload time (used when removing dumplicates)
    data.sort_values("uploadTime", ascending=False, inplace=True)
    groups = data.groupby(by="type")

    # check to see if person is looping
    if "basal" in data["type"].unique():
        basal = groups.get_group("basal").dropna(axis=1, how="all")
        if "deliveryType" in list(basal):
            bd = basal.loc[
                basal["deliveryType"] == "temp",
                ["date", "deliveryType"]
            ]
            temp_basal_counts = (
                pd.DataFrame(
                    bd.groupby("date").deliveryType.count()
                ).reset_index()
            )
            temp_basal_counts.rename(
                {"deliveryType": "tempBasalCounts"},
                axis=1,
                inplace=True
            )
            data = pd.merge(data, temp_basal_counts, on="date", how="left")
            # >= 25 temp basals per day is likely looping
            data["isLoopDay"] = data["tempBasalCounts"] >= 25
            # redefine groups with the new data
            groups = data.groupby(by="type")

        else:
            data["isLoopDay"] = np.nan
    else:
        data["isLoopDay"] = np.nan

    # %% CGM DATA
    if "cbg" in data["type"].unique():
        # sort data with
        metadata["cgmData"] = True

        # filter by cgm
        cgm = groups.get_group("cbg").copy()

        # sort data
        cgm.sort_values("roundedUtcTime", ascending=False, inplace=True)
        cgm.reset_index(drop=False, inplace=True)

        # calculate cgm in mg/dL
        cgm["mg/dL"] = round(cgm["value"] * MGDL_PER_MMOLL)

        # get rid of spike data
        cgm, nSpike = remove_spike_data(cgm.copy())
        metadata["nSpike"] = nSpike

        # assign upload cgm device info to cgm records in that upload
        cgm = add_upload_info_to_cgm_records(groups, cgm.copy())

        # check to see if cgm info exists in healthkit locations
        cgm = expand_heathkit_cgm_fields(cgm.copy())

        # replace smoothed cgm values with raw values (if they exist)
        # this must run after expand_heathkit_cgm_fields _
        cgm["mg/dL"], metadata["nSmoothedCgmReplaced"] = (
            replace_smoothed_cgm_values(cgm.copy())
        )

        # get cgm models
        cgm["cgmModel"], cgm["cgmModelSensedFrom"] = np.nan, np.nan

        # dexcom cgm models (G4, G5, G6)
        cgm[["cgmModel", "cgmModelSensedFrom"]] = (
            get_dexcom_cgm_model(cgm.copy())
        )

        # for non dexcom cgms
        # 670G, 640G, 630G, 530G, 523/723, libre, animas, and tandem
        cgm[["cgmModel", "cgmModelSensedFrom"]] = (
            get_non_dexcom_cgm_model(cgm.copy())
        )

        # get metadata on cgm models and devices
        metadata["nMissingCgmModels"] = cgm["cgmModel"].isnull().sum()
        metadata["uniqueCgmModels"] = str(cgm["cgmModel"].unique())
        if "deviceId" in list(cgm):
            metadata["uniqueCgmDevices"] = str(cgm["deviceId"].unique())

        #  clean distributions
        # break up all traces by cgm model
        combined_cgm_series = pd.DataFrame()
        cgm_models = cgm.groupby(by="cgmModel")

        for cgm_model in cgm_models.groups.keys():
            print("working on", cgm_model)
            temp_cgm = cgm_models.get_group(cgm_model)

            # get rid of cgm values too low/high (< 38 & > 402 mg/dL)
            temp_cgm, nInvalidCgmValues = remove_invalid_cgm_values(temp_cgm)
            metadata["nInvalidCgmValues." + cgm_model] = nInvalidCgmValues

            # sort by upload time before getting rid of duplicates
            temp_cgm.sort_values("uploadTime", ascending=False, inplace=True)

            # get rid of duplicates that have the same ["deviceTime", "mg/dL"]
            temp_cgm, n_cgm_dups_removed = (
                removeCgmDuplicates(temp_cgm, "deviceTime", "mg/dL")
            )
            metadata["nCgmDuplicatesRemovedDeviceTime." + cgm_model] = (
                n_cgm_dups_removed
            )

            # get rid of duplicates that have the same ["time", "mg/dL"]
            temp_cgm, n_cgm_dups_removed = (
                removeCgmDuplicates(temp_cgm, "utcTime", "mg/dL")
            )
            metadata["nCgmDuplicatesRemovedUtcTime." + cgm_model] = (
                n_cgm_dups_removed
            )

            # get rid of duplicates that have the same roundedTime
            temp_cgm, n_cgm_dups_removed = (
                removeDuplicates(temp_cgm, "roundedUtcTime")
            )
            metadata["nCgmDuplicatesRemovedRoundedTime." + cgm_model] = (
                n_cgm_dups_removed
            )

            # create a contiguous 5 minute time series
            first_day = temp_cgm["roundedUtcTime"].min()
            metadata["firstCgm." + cgm_model] = first_day

            last_day = temp_cgm["roundedUtcTime"].max()
            metadata["lastCgm." + cgm_model] = last_day

            rng = pd.date_range(first_day, last_day, freq="5min")
            contiguous_data = pd.DataFrame(
                rng,
                columns=["roundedUtcTime"]
            ).sort_values(
                "roundedUtcTime",
                ascending=False
            ).reset_index(drop=True)

            # merge with cgm data
            cgm_series = pd.merge(
                contiguous_data,
                temp_cgm[[
                    "roundedUtcTime", "hashid", "isLoopDay",
                    "cgmModel", "age", "ylw", "mg/dL"
                 ]],
                on="roundedUtcTime",
                how="left"
            )

            # sort so that the oldest data point is on top
            cgm_series.sort_values(
                "roundedUtcTime", ascending=True, inplace=True
            )
            cgm_series.reset_index(drop=True, inplace=True)

            # get dexcom icgm bins
            value_bins = np.array(
                [37, 39, 60, 80, 120, 160, 200, 250, 300, 350, 400, 403]
            )
            value_bin_names = (
                "< 40", "40-60", "61-80", "81-120", "121-160", "161-200",
                "201-250", "251-300", "301-350", "351-400", "> 400"
            )
            cgm_series["valueBin"] = pd.cut(
                cgm_series["mg/dL"], value_bins, labels=value_bin_names
            )

            # get the previous val
            cgm_series["previousVal"] = cgm_series["mg/dL"].shift(1)

            # get difference between current and previous val
            cgm_series["diffFromPrevVal"] = (
                cgm_series["mg/dL"] - cgm_series["previousVal"]
            )

            # calculate the rate from previous value (mg/dL/min)
            cgm_series["rateFromPrevVal"] = cgm_series["diffFromPrevVal"] / 5

            # get dexcom icgm rate bins
            rate_bins = np.array(
                [-100, -2.000001, -1.000001, -0.000001, 1, 2, 100]
            )
            # NOTE: bracket means include, parentheses means exclude
            rate_bin_names = (
                "< -2", "[-2,-1)", "[-1,-0)", "[0,1]", "(1,2]", ">2",
            )
            cgm_series["rateBin"] = pd.cut(
                cgm_series["rateFromPrevVal"], rate_bins, labels=rate_bin_names
            )

            # through in the join category
            cgm_series["valAndRateBin"] = (
                cgm_series["valueBin"].astype(str)
                + " & "
                + cgm_series["rateBin"].astype(str)
            )

            # calculate slope (mg/dL/min) over the last 15, 30, and 60 minutes
            cgm_series["slope15"] = (
                cgm_series["mg/dL"].rolling(3).apply(get_slope, raw=True)
            )

            cgm_series["slope30"] = (
                cgm_series["mg/dL"].rolling(6).apply(get_slope, raw=True)
            )

            cgm_series["slope60"] = (
                cgm_series["mg/dL"].rolling(12).apply(get_slope, raw=True)
            )

            # add in the next value
            cgm_series["nextVal"] = cgm_series["mg/dL"].shift(-1)

            # get difference or relative increase/decrease of next value
            cgm_series["relativeNextValue"] = (
                cgm_series["nextVal"] - cgm_series["mg/dL"]
            )

            # rate of next value
            cgm_series["rateToNextVal"] = cgm_series["relativeNextValue"] / 5

            # drop rows where there is no information
            cgm_series.dropna(subset=['hashid'], inplace=True)
            metadata["nCgmDataPoints." + cgm_model] = len(cgm_series)

            # append cgm model to a larger table
            combined_cgm_series = pd.concat(
                [combined_cgm_series, cgm_series],
                ignore_index=True
            )
        if len(combined_cgm_series) > 0:
            # sort so that the oldest data point is on top
            # and that the G5_G6 get deleted if they are apart of a duplicate
            combined_cgm_series["cgmModel_G5_and_G6"] = (
                combined_cgm_series["cgmModel"] == "G5_G6"
            )
            combined_cgm_series.sort_values(
                by=["roundedUtcTime", "cgmModel_G5_and_G6", "cgmModel"],
                ascending=[False, True, False],
                inplace=True
            )
            combined_cgm_series.reset_index(drop=True, inplace=True)

            # add in check to see if there are duplicates between cgm devices
            nUnique_cgm_times = len(combined_cgm_series["roundedUtcTime"].unique())
            cgm_len = len(combined_cgm_series)
            metadata["duplicateCgmDataIssue"] = nUnique_cgm_times != cgm_len

            nDuplicate_cgm = cgm_len - nUnique_cgm_times
            metadata["nDuplicateCgmDataIssues"] = nDuplicate_cgm

            # if there are still duplicates, get rid of them
            if nDuplicate_cgm > 0:
                # save the duplicates for further examination
                combined_cgm_series.to_csv(os.path.join(
                    debug_duplicates,
                    "PHI-" + userid + "-cgm-series-has-cgm-duplicates.csv.gz"
                ))

                cgm.to_csv(os.path.join(
                    debug_duplicates,
                    "PHI-" + userid + "-cgm-data-has-cgm-duplicates.csv.gz"
                ))

                # get rid of duplicates
                combined_cgm_series, n_cgm_dups_removed = (
                    removeDuplicates(combined_cgm_series, "roundedUtcTime")
                )
                metadata["nCgmDuplicatesRemovedRoundedTime.atEnd"] = (
                    n_cgm_dups_removed
                )
            metadata["nCgmDataPoints.atEnd"] = len(combined_cgm_series)

            # add whether data is dexcom cgm or not
            combined_cgm_series["dexcomCgm"] = (
                combined_cgm_series["cgmModel"].astype(str).str.contains("G4|G5|G6")
            )

            # save distribution data
            combined_cgm_series.to_csv(os.path.join(
                output_distribution,
                "PHI-" + userid + "-cgm-distribution.csv.gz"
            ))

            # get cgm stats
            # create a contiguous 5 minute time series of ALL cgm data
            first_day = combined_cgm_series["roundedUtcTime"].min()
            metadata["firstCgm." + cgm_model] = first_day

            last_day = combined_cgm_series["roundedUtcTime"].max()
            metadata["lastCgm." + cgm_model] = last_day

            rng = pd.date_range(first_day, last_day, freq="5min")
            contiguous_data = pd.DataFrame(
                rng,
                columns=["roundedUtcTime"]
            ).sort_values(
                "roundedUtcTime",
                ascending=True
            ).reset_index(drop=True)

            # merge with combined_cgm_series data
            all_cgm = pd.merge(
                contiguous_data,
                combined_cgm_series[[
                    'roundedUtcTime', 'hashid', 'cgmModel', 'dexcomCgm',
                    'age', 'ylw', 'isLoopDay', 'mg/dL',
                ]],
                on="roundedUtcTime",
                how="left"
            )

            # get cgm stats
            # get a binary (T/F) of whether we have a cgm value
            all_cgm["hasCgm"] = all_cgm["mg/dL"].notnull()

            # fill isLoopDay nan with False
            all_cgm["isLoopDay"].fillna(False, inplace=True)

            # has loop and cgm
            all_cgm["hasLoopAndCgm"] = (
                (all_cgm["isLoopDay"]) & (all_cgm["hasCgm"])
            )

            all_cgm["hasCgmWithoutLoop"] = (
                (~all_cgm["isLoopDay"]) & (all_cgm["hasCgm"])
            )

            # make this a function and round ascendingly
            ts39_401 = all_cgm["mg/dL"].copy()

            # for all the less than (<) criteria
            for cgm_threshold in [40, 54, 70]:
                all_cgm["cgm < " + str(cgm_threshold)] = (
                    ts39_401.lt(cgm_threshold)
                )
            # for all the greter than or equal to (>=) criteria
                all_cgm["cgm >= " + str(cgm_threshold)] = (
                    ts39_401.ge(cgm_threshold)
                )

            # for all the the less than or equal to (<=) criteria
            for cgm_threshold in [140, 180, 250, 300, 400]:
                all_cgm["cgm <= " + str(cgm_threshold)] = (
                    ts39_401.le(cgm_threshold)
                )
            # for all the the greter than (>) criteria
                all_cgm["cgm > " + str(cgm_threshold)] = (
                    ts39_401.gt(cgm_threshold)
                )

            # get all of the cgm ranges
            # (cgm >= 40) & (cgm < 54)
            all_cgm["40 <= cgm < 54"] = (
                (all_cgm["cgm >= 40"]) & (all_cgm["cgm < 54"])
            )

            # (cgm >= 54) & (cgm < 70)
            all_cgm["54 <= cgm < 70"] = (
                (all_cgm["cgm >= 54"]) & (all_cgm["cgm < 70"])
            )

            # (cgm >= 70) & (cgm <= 140)
            all_cgm["70 <= cgm <= 140"] = (
                (all_cgm["cgm >= 70"]) & (all_cgm["cgm <= 140"])
            )

            # (cgm >= 70) & (cgm <= 180)
            all_cgm["70 <= cgm <= 180"] = (
                (all_cgm["cgm >= 70"]) & (all_cgm["cgm <= 180"])
            )

            # (cgm > 180) & (cgm <= 250)
            all_cgm["180 < cgm <= 250"] = (
                (all_cgm["cgm > 180"]) & (all_cgm["cgm <= 250"])
            )

            # (cgm > 250) & (cgm <= 400)
            all_cgm["250 < cgm <= 400"] = (
                (all_cgm["cgm > 250"]) & (all_cgm["cgm <= 400"])
            )

            # derfine the windows to calculate the stats over
            window_names = ["hour", "day", "week", "month", "quarter", "year"]
            window_lengths = [12,    288,   288*7,  288*7*4, 288*90,   288*365]

            for w_name, w_len in zip(window_names, window_lengths):
                # require lenth of window for percent calculations
                w_min = w_len

                # get the start and end times for each window
                all_cgm[w_name + ".startTime"] = (
                    all_cgm["roundedUtcTime"].shift(w_len - 1)
                )
                all_cgm[w_name + ".endTime"] = all_cgm["roundedUtcTime"]

                # add majority age for the time period
                all_cgm[w_name + ".age"] = np.round(
                    all_cgm["age"].rolling(
                        min_periods=1,
                        window=w_len
                    ).mean()
                )

                # add majority ylw for the time period
                all_cgm[w_name + ".ylw"] = np.round(
                    all_cgm["ylw"].rolling(
                        min_periods=1,
                        window=w_len
                    ).median()
                )

                # get percent time cgm used
                all_cgm[w_name + ".cgmPercent"] = (
                    all_cgm["hasCgm"].rolling(
                        min_periods=w_min,
                        window=w_len
                    ).sum() / w_len
                )

                # get the total number of non-null values over this time period
                all_cgm[w_name + ".missingCgmPercent"] = (
                    1 - all_cgm[w_name + ".cgmPercent"]
                )

                # create (T/F) 70 and 80 percent available thresholds
                # which will be useful for processing later
                all_cgm[w_name + ".ge70Available"] = (
                    all_cgm[w_name + ".cgmPercent"] >= 0.7
                )

                all_cgm[w_name + ".ge80Available"] = (
                    all_cgm[w_name + ".cgmPercent"] >= 0.8
                )

                # get percent time Loop was used NOTE: this is
                # approximate because we use > 24 temp basals per day
                # ALSO: this is percent time Loop was used while cgm in use
                all_cgm[w_name + ".loopingAndCgmPercent"] = (
                    all_cgm["hasLoopAndCgm"].rolling(
                        min_periods=w_min,
                        window=w_len
                    ).sum() / w_len
                )

                # percent of time cgm without loop
                all_cgm[w_name + ".cgmWithoutLoopPercent"] = (
                    all_cgm["hasCgmWithoutLoop"].rolling(
                        min_periods=w_min,
                        window=w_len
                    ).sum() / w_len
                )

                # get percent time in different ranges
                # % Time < 54
                all_cgm[w_name + ".lt54Percent"] = (
                    all_cgm["cgm < 54"].rolling(
                        min_periods=w_min,
                        window=w_len
                    ).sum() / w_len
                )

                # % Time in 54-70 (cgm >= 54) & (cgm < 70)
                all_cgm[w_name + ".bt54_70Percent"] = (
                    all_cgm["54 <= cgm < 70"].rolling(
                        min_periods=w_min,
                        window=w_len
                    ).sum() / w_len
                )

                # % Time in target range (cgm >= 70) & (cgm <= 180)
                all_cgm[w_name + ".bt70_180Percent"] = (
                    all_cgm["70 <= cgm <= 180"].rolling(
                        min_periods=w_min,
                        window=w_len
                    ).sum() / w_len
                )

                # % Time in 180-250 (cgm > 180) & (cgm <= 250)
                all_cgm[w_name + ".bt180_250Percent"] = (
                    all_cgm["180 < cgm <= 250"].rolling(
                        min_periods=w_min,
                        window=w_len
                    ).sum() / w_len
                )

                # % Time > 250
                all_cgm[w_name + ".gt250Percent"] = (
                    all_cgm["cgm > 250"].rolling(
                        min_periods=w_min,
                        window=w_len
                    ).sum() / w_len
                )

                # check that all of the percentages add of to 1 or 100%
                all_cgm[w_name + ".percentCheck"] = (
                     all_cgm[w_name + ".missingCgmPercent"]
                     + all_cgm[w_name + ".lt54Percent"]
                     + all_cgm[w_name + ".bt54_70Percent"]
                     + all_cgm[w_name + ".bt70_180Percent"]
                     + all_cgm[w_name + ".bt180_250Percent"]
                     + all_cgm[w_name + ".gt250Percent"]
                )

                # here are some other less common percent time in ranges
                # % Time < 70
                all_cgm[w_name + ".lt70Percent"] = (
                    all_cgm["cgm < 70"].rolling(
                        min_periods=w_min,
                        window=w_len
                    ).sum() / w_len
                )

                # % Time in target range (cgm >= 70) & (cgm <= 140)
                all_cgm[w_name + ".tir70to140Percent"] = (
                    all_cgm["70 <= cgm <= 140"].rolling(
                        min_periods=w_min,
                        window=w_len
                    ).sum() / w_len
                )

                # percent time above a threshold
                # % Time > 180
                all_cgm[w_name + ".gt180Percent"] = (
                    all_cgm["cgm > 180"].rolling(
                        min_periods=w_min,
                        window=w_len
                    ).sum() / w_len
                )

                # points that are 39 or 401 should NOT be used most
                # calculations because the actual number is <= 39 or >= 401
                # (cgm < 40) OR (cgm > 400)
                all_cgm["mg/dL.40to400"] = (
                    ts39_401.replace(to_replace=39, value=np.nan)
                )

                all_cgm["mg/dL.40to400"] = (
                    all_cgm["mg/dL.40to400"].replace(
                        to_replace=401,
                        value=np.nan
                    )
                )

                # redefine the time series (ts) for the following stats
                ts40_400 = all_cgm["mg/dL.40to400"].copy()
                # require at least 3 points to make a stats calculation
                w_min = 3

                # recalcuate percent of measurements available
                all_cgm[w_name + ".40to400availablePercent"] = (
                    ts40_400.rolling(min_periods=w_min, window=w_len).count()
                ) / w_len

                # get the total number of non-null values over this time period
                all_cgm[w_name + ".40to400missingPercent"] = (
                    1 - all_cgm[w_name + ".40to400availablePercent"]
                )

                all_cgm[w_name + ".40to400ge70Available"] = (
                    all_cgm[w_name + ".40to400availablePercent"] >= 0.7
                )

                all_cgm[w_name + ".40to400ge80Available"] = (
                    all_cgm[w_name + ".40to400availablePercent"] >= 0.8
                )

                # create a rolling object
                roll40_400 = ts40_400.rolling(min_periods=w_min, window=w_len)

                # quantiles
                # NOTE: this will increase run time, so only run if you need
                # 3-4X the processing time since it has to sort the data
                # TODO: make this an option to the function, once it is made

                # min
                all_cgm[w_name + ".min"] = roll40_400.min()

                # 10, 25, 75, and 90th percentiles
                all_cgm[w_name + ".10th"] = roll40_400.quantile(0.10)
                all_cgm[w_name + ".25th"] = roll40_400.quantile(0.25)
                all_cgm[w_name + ".75th"] = roll40_400.quantile(0.75)
                all_cgm[w_name + ".90th"] = roll40_400.quantile(0.90)

                # max
                all_cgm[w_name + ".max"] = roll40_400.max()

                # median
                all_cgm[w_name + ".median"] = roll40_400.median()

                # iqr
                all_cgm[w_name + ".iqr"] = (
                    all_cgm[w_name + ".75th"] - all_cgm[w_name + ".25th"]
                )

                # mean
                all_cgm[w_name + ".mean"] = roll40_400.mean()

                # GMI(%) = 3.31 + 0.02392 x [mean glucose in mg/dL]
                all_cgm[w_name + ".gmi"] = (
                    3.31 + (0.02392 * all_cgm[w_name + ".mean"])
                )

                # standard deviation (std)
                all_cgm[w_name + ".std"] = roll40_400.std()

                # coefficient of variation (cov) = std / mean
                all_cgm[w_name + ".cov"] = (
                    all_cgm[w_name + ".std"] / all_cgm[w_name + ".mean"]
                )

                # make an episodes dataframe, and then get stats
                # get episodes < 54
                episode_ts = get_episodes(
                    all_cgm[["roundedUtcTime", "hasCgm", "cgm < 54"]].copy(),
                    "cgm < 54",
                    15
                )
                all_cgm = pd.concat([all_cgm, episode_ts], axis=1)

                # get episodes < 70
                episode_ts = get_episodes(
                    all_cgm[["roundedUtcTime", "hasCgm", "cgm < 70"]].copy(),
                    "cgm < 70",
                    15
                )
                all_cgm = pd.concat([all_cgm, episode_ts], axis=1)

                # get rolling stats on episodes
                pdb.set_trace()

                # %% save cgm stats data
                all_cgm.to_csv(os.path.join(
                    output_stats,
                    "PHI-" + userid + "-cgm-stats.csv.gz"
                ))

        print(metadata.T)

    else:
        metadata["cgmData"] = False
        print(d_idx, "no cgm data")

    # save metadata
    metadata.to_csv(os.path.join(
        output_metadata,
        "PHI-" + userid + "-cgm-metadata.csv.gz"
    ))

    print("finished", d_idx, userid)
