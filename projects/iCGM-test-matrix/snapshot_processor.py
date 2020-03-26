#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Snapshot Processor
==================
:File: snapshot_processor.py
:Description: Converts a Tidepool data snapshot into a set of dataframes that
              can be used by a risk simulator.
:Version: 0.0.1
:Created: 2020-02-04
:Authors: Jason Meno (jam)
:Dependencies: A .csv containing Tidepool CGM device data
:License: BSD-2-Clause
"""

# %% Imports
import pandas as pd
import numpy as np
import time
import datetime
import ast
import os
import icgm_condition_finder as cond_finder
# %% Functions


def get_active_schedule(data,
                        snapshot_df,
                        file_name,
                        evaluation_time):
    """Get pumpSettings row of active schedules used during the snapshot."""
    # Get all schedules and their upload ids
    schedules = data[data.activeSchedule.notnull()].copy()

    if len(schedules) == 0:
        print("NO ACTIVE SCHEDULES FOUND IN DATA!")
        active_schedule = np.nan

    else:
        # Get the nearest pump uploadId to the evaluation_time
        snapshot_uploadId = \
            snapshot_df.loc[((snapshot_df.type == 'bolus') |
                            (snapshot_df.type == 'basal')),
                            'uploadId'].values[0]

        active_schedule = \
            schedules[schedules.uploadId == snapshot_uploadId]

        # If no matching uploadId is found OR more multiple schedule are found,
        # then historical schedule records should be available.
        # Pick the one closest prior to the time of evaluation.
        if (len(active_schedule) > 1) | (len(active_schedule) == 0):
            nearest_time = \
                schedules.loc[
                    schedules.rounded_local_time < evaluation_time,
                    'rounded_local_time'].max()

            active_schedule = \
                schedules[(
                    schedules.rounded_local_time == nearest_time)
                    ]

            # If two active schedules are set within 5 minutes of each other
            # Select the last one
            if(len(active_schedule) > 1):
                active_schedule = active_schedule.head(1)

        # If no active schedule can STILL be found, then there is no matching
        # uploadid or nearby historical record. The schedule may be able to be
        # reverse-engineered from actual bolus entry settings metadata.

        # For now, select the schedule closest to the evaluation point

        if (len(active_schedule) == 0):
            print("NO ACTIVE SCHEDULE MATCHED - FORCED SELECTION")
            schedules['distances_from_evaluation'] = \
                abs(schedules.rounded_local_time - evaluation_time)

            min_distance = schedules['distances_from_evaluation'].min()
            active_schedule = \
                schedules[
                    schedules['distances_from_evaluation'] == min_distance
                    ]

    return active_schedule


def get_relative_timestamp(timestamp_ms):
    """Calculate the HH:MM:SS strftime from midnight using a relative timestamp
    in milliseconds"""

    timestamp_seconds = timestamp_ms/1000

    # To calculate relative HH:MM:SS start times,
    # 2020-01-01 00:00:00 is chosen
    relative_offset_seconds = 1577854800

    full_time_seconds = timestamp_seconds + relative_offset_seconds

    relative_timestamp = \
        datetime.datetime.fromtimestamp(full_time_seconds).strftime('%H:%M:%S')

    return relative_timestamp


def get_basal_rates(active_schedule, basal_df):
    """Get the basal rates from the active schedule"""
    df_columns = ['basal_rate_start_times',
                  'basal_rate_minutes',
                  'basal_rate_values',
                  'actual_basal_rates',
                  'basal_rate_units']

    basal_rates = pd.DataFrame(columns=df_columns)

    basal_schedules = \
        ast.literal_eval(active_schedule.basalSchedules.values[0])

    active_name = active_schedule.activeSchedule.values[0]
    active_basal_rates = basal_schedules.get(active_name)

    start_times = []

    # If no basal rates were found, the schedule's entry is blank
    # Use the weighted average used from data's basal rates
    if len(active_basal_rates) == 0:
        print("\nUSING WEIGHTED BASAL RATE HISTORY FOR BR\n")

        basal_df["duration_hours"] = basal_df["duration"]/1000/60/60

        weighted_avg_basal_rate = (
            np.sum(basal_df["rate"] * basal_df["duration_hours"])
            / basal_df["duration_hours"].sum()
        )

        # Round to nearest 0.05 U/hr
        weighted_avg_basal_rate = (
            round(round(weighted_avg_basal_rate/0.05)*0.05, 2)
        )

        start_string = datetime.time(0, 0).strftime('%H:%M:%S')
        start_times.append(0)
        basal_rates.loc[0, 'basal_rate_start_times'] = start_string
        basal_rates.loc[0, 'basal_rate_values'] = weighted_avg_basal_rate

    else:
        for rate_loc in range(len(active_basal_rates)):
            rate_info = active_basal_rates[rate_loc]
            rate = rate_info.get('rate')
            start_time = rate_info.get('start')
            start_times.append(start_time)
            start_string = get_relative_timestamp(start_time)

            basal_rates.loc[rate_loc, 'basal_rate_start_times'] = start_string
            basal_rates.loc[rate_loc, 'basal_rate_values'] = rate

    basal_rates['actual_basal_rates'] = basal_rates['basal_rate_values']
    basal_rates['basal_rate_units'] = 'U/hr'

    # Add 24 hours in ms to the start_times list
    # for calculating the differential in minutes
    start_times.append(24 * 60 * 60 * 1000)
    basal_rates['basal_rate_minutes'] = np.diff(start_times)/1000/60

    return basal_rates


def get_carb_ratios(active_schedule, bolus_df):
    """Get the carb to insulin ratio(s) from the active schedule"""

    df_columns = ['carb_ratio_start_times',
                  'carb_ratio_values',
                  'actual_carb_ratios',
                  'carb_ratio_value_units']

    carb_ratios = pd.DataFrame(columns=df_columns)

    if 'carbRatios' in active_schedule:
        carb_ratio_schedules = \
            ast.literal_eval(active_schedule.carbRatios.values[0])
        active_name = active_schedule.activeSchedule.values[0]
        active_carb_ratios = carb_ratio_schedules.get(active_name)
    elif 'carbRatio' in active_schedule:
        active_carb_ratios = \
            ast.literal_eval(active_schedule.carbRatio.values[0])
    else:
        print("NO CARB RATIOS!")

    # If no carb ratios were found, the schedule's entry is blank
    # Use the average ratio used from data's bolus calculations
    if len(active_carb_ratios) == 0:
        print("\nUSING BOLUS CALCULATOR ENTRIES FOR CIR\n")

        ratio = bolus_df.insulinCarbRatio.astype(float).mean().round()
        start_string = datetime.time(0, 0).strftime('%H:%M:%S')

        carb_ratios.loc[0, 'carb_ratio_start_times'] = start_string
        carb_ratios.loc[0, 'carb_ratio_values'] = ratio

    else:
        for ratio_loc in range(len(active_carb_ratios)):
            ratio_info = active_carb_ratios[ratio_loc]
            ratio = ratio_info.get('amount')
            start_time = ratio_info.get('start')
            start_string = get_relative_timestamp(start_time)

            carb_ratios.loc[ratio_loc, 'carb_ratio_start_times'] = start_string
            carb_ratios.loc[ratio_loc, 'carb_ratio_values'] = ratio

    carb_ratios['actual_carb_ratios'] = carb_ratios['carb_ratio_values']
    carb_ratios['carb_ratio_value_units'] = 'g/U'

    return carb_ratios


def get_isfs(active_schedule, bolus_df):
    """Get the insulin sensitivity ratio(s) from the active schedule"""

    df_columns = ['sensitivity_ratio_start_times',
                  'sensitivity_ratio_end_times',
                  'sensitivity_ratio_values',
                  'actual_sensitivity_ratios',
                  'sensitivity_ratio_value_units']

    isfs = pd.DataFrame(columns=df_columns)

    if 'insulinSensitivities' in active_schedule:
        isf_schedules = \
            ast.literal_eval(active_schedule.insulinSensitivities.values[0])
        active_name = active_schedule.activeSchedule.values[0]
        active_isfs = isf_schedules.get(active_name)
    elif 'insulinSensitivity' in active_schedule:
        active_isfs = \
            ast.literal_eval(active_schedule.insulinSensitivity.values[0])
    else:
        print("NO ISFS FOUND!")

    start_times = []

    # If no isfs were found, the schedule's entry is blank
    # Use the average isf used from data's bolus calculations
    if len(active_isfs) == 0:
        print("\nUSING BOLUS CALCULATOR ENTRIES FOR ISF\n")

        isf = bolus_df.insulinSensitivity.astype(float).mean()
        isf = round(isf*18.01559)
        start_string = datetime.time(0, 0).strftime('%H:%M:%S')
        start_times.append(start_string)

        isfs.loc[0, 'sensitivity_ratio_start_times'] = start_string
        isfs.loc[0, 'sensitivity_ratio_values'] = isf

    else:
        for isf_loc in range(len(active_isfs)):
            isf_info = active_isfs[isf_loc]
            isf = round(isf_info.get('amount')*18.01559)

            start_time = isf_info.get('start')
            start_string = get_relative_timestamp(start_time)
            start_times.append(start_string)

            isfs.loc[isf_loc, 'sensitivity_ratio_start_times'] = start_string
            isfs.loc[isf_loc, 'sensitivity_ratio_values'] = isf

    # Check if sensitivity ratios were improperly converted from mg/dL
    if any(isfs['sensitivity_ratio_values'] > 500):
        isfs['sensitivity_ratio_values'] = \
            (isfs['sensitivity_ratio_values'].astype(float)/18.01559).round()

    isfs['actual_sensitivity_ratios'] = isfs['sensitivity_ratio_values']
    isfs['sensitivity_ratio_value_units'] = 'mg/dL/U'

    # Shift start times by -1 to form the end times
    end_times = start_times[1:] + [start_times[0]]
    isfs['sensitivity_ratio_end_times'] = end_times

    return isfs


def get_target_ranges(active_schedule, bolus_df):
    """Get the target BG ranges from the active schedule"""

    df_columns = ['target_range_start_times',
                  'target_range_end_times',
                  'target_range_minimum_values',
                  'target_range_maximum_values',
                  'target_range_value_units']

    df_target_range = pd.DataFrame(columns=df_columns)

    if 'bgTargets' in active_schedule:
        target_schedules = \
            ast.literal_eval(active_schedule.bgTargets.values[0])

        active_name = active_schedule.activeSchedule.values[0]
        active_targets = target_schedules.get(active_name)
    elif 'bgTarget' in active_schedule:
        active_targets = ast.literal_eval(active_schedule.bgTarget.values[0])
    elif 'bgTarget.start' in active_schedule:
        target_start = int(active_schedule['bgTarget.start'].values)
        active_targets = dict({'start': target_start})

        if 'bgTarget.target' in active_schedule:
            bg_target = float(active_schedule['bgTarget.target'].values)
            active_targets.update({'target': bg_target})

        if 'bgTarget.range' in active_schedule:
            target_range = float(active_schedule['bgTarget.range'].values)
            active_targets.update({'range': target_range})

        if 'bgTarget.high' in active_schedule:
            target_high = float(active_schedule['bgTarget.high'].values)
            active_targets.update({'high': target_high})

        if 'bgTarget.low' in active_schedule:
            target_low = float(active_schedule['bgTarget.low'].values)
            active_targets.update({'low': target_low})

        active_targets = [active_targets]

    else:
        print("NO TARGET RANGES!")

    start_times = []

    # If no targets were found, the schedule's entry is blank
    # Use the min/max bgTarget.target used from data's bolus calculations
    if len(active_targets) == 0:
        print("\nUSING BOLUS CALCULATOR ENTRIES FOR TARGETS\n")

        min_target = bolus_df['bgTarget.target'].astype(float).min()
        min_target = round(min_target*18.01559)

        max_target = bolus_df['bgTarget.target'].astype(float).max()
        max_target = round(max_target*18.01559)

        start_string = datetime.time(0, 0).strftime('%H:%M:%S')
        start_times.append(start_string)

        df_target_range.loc[0, 'target_range_start_times'] = start_string
        df_target_range.loc[0, 'target_range_minimum_values'] = min_target
        df_target_range.loc[0, 'target_range_maximum_values'] = max_target

    else:
        for target_loc in range(len(active_targets)):
            target_info = active_targets[target_loc]
            start_time = target_info.get('start')
            start_string = get_relative_timestamp(start_time)
            start_times.append(start_string)

            df_target_range.loc[target_loc,
                                'target_range_start_times'] = start_string

            if 'target' in target_info.keys():
                target = round(target_info.get('target')*18.01559)
                df_target_range.loc[target_loc,
                                    'target_range_minimum_values'] = \
                    target
                df_target_range.loc[target_loc,
                                    'target_range_maximum_values'] = \
                    target

            if 'range' in target_info.keys():
                target_range = round(target_info.get('range')*18.01559)
                df_target_range.loc[target_loc,
                                    'target_range_minimum_values'] = \
                    target - target_range

                df_target_range.loc[target_loc,
                                    'target_range_maximum_values'] = \
                    target + target_range

            if 'high' in target_info.keys():
                target_high = round(target_info.get('high')*18.01559)
                df_target_range.loc[target_loc,
                                    'target_range_maximum_values'] = \
                    target_high

            if 'low' in target_info.keys():
                target_low = round(target_info.get('high')*18.01559)
                df_target_range.loc[target_loc,
                                    'target_range_minimum_values'] = \
                    target_low

    df_target_range['target_range_value_units'] = 'mg/dL'

    # Shift start times by -1 to form the end times
    end_times = start_times[1:] + [start_times[0]]
    df_target_range['target_range_end_times'] = end_times

    # Check if bg targets were improperly converted from mg/dL
    if any(df_target_range['target_range_minimum_values'] > 500):
        df_target_range['target_range_minimum_values'] = \
            (df_target_range['target_range_minimum_values'].astype(float) /
             18.01559).round()

    if any(df_target_range['target_range_maximum_values'] > 500):
        df_target_range['target_range_maximum_values'] = \
            (df_target_range['target_range_maximum_values'].astype(float) /
             18.01559).round()

    return df_target_range


def get_carb_events(snapshot_df):
    """Get carb events from the carbInput during boluses"""

    df_columns = ['carb_dates',
                  'carb_values',
                  'actual_carbs',
                  'carb_absorption_times',
                  'carb_value_units']

    carb_events = pd.DataFrame(columns=df_columns)

    carb_df = snapshot_df[snapshot_df.carbInput > 0]
    carb_df = \
        carb_df.groupby('rounded_local_time').carbInput.sum().reset_index()

    carb_events['carb_dates'] = \
        carb_df.rounded_local_time.dt.strftime("%Y-%m-%d %H:%M:%S")
    carb_events['carb_values'] = carb_df.carbInput
    carb_events['actual_carbs'] = carb_events['carb_values']
    carb_events['carb_absorption_times'] = 180
    carb_events['carb_value_units'] = 'g'

    return carb_events


def get_dose_events(snapshot_df):
    """Create a dose_events dataframe containing boluses, extended boluses,
    temp basals, and suspend events"""

    df_columns = ['dose_types',
                  'dose_start_times',
                  'dose_end_times',
                  'dose_values',
                  'actual_doses',
                  'dose_value_units']

    dose_events = pd.DataFrame(columns=df_columns)

    bolus_events = dose_events.copy()
    extended_events = dose_events.copy()
    temp_basal_events = dose_events.copy()
    suspend_events = dose_events.copy()

    bolus_df = snapshot_df[snapshot_df.type == 'bolus'].copy()

    if len(bolus_df) > 0:
        # Merge boluses together into single 5-minute timestamps
        bolus_df = pd.DataFrame(
            bolus_df.groupby('rounded_local_time').normal.sum()
        ).reset_index()

        bolus_events['dose_values'] = bolus_df['normal']
        bolus_events['dose_start_times'] = bolus_df['rounded_local_time']
        bolus_events['dose_end_times'] = bolus_df['rounded_local_time']
        bolus_events['dose_types'] = 'DoseType.bolus'
        bolus_events['dose_value_units'] = 'U'

        if('extended' in list(bolus_df)):
            extended_df = bolus_df[bolus_df.extended > 0]
        else:
            extended_df = pd.DataFrame()

        if len(extended_df) > 0:
            extended_df = bolus_df[bolus_df.subType == 'dual/square']

            # NOTE: Multiple extended entries may exist within the same rounded
            # timestamp.

            extended_events['dose_values'] = extended_df['extended']
            extended_events['dose_start_times'] = \
                extended_df['rounded_local_time']
            extended_events['dose_end_times'] = \
                extended_df.apply(
                    lambda x: x['rounded_local_time'] +
                    datetime.timedelta(milliseconds=x['duration']),
                    axis=1)

            extended_events['dose_types'] = 'DoseType.extended'
            extended_events['dose_value_units'] = 'U'

    basal_df = snapshot_df[snapshot_df.deliveryType == 'temp'].copy()

    if len(basal_df) > 0:

        # Merge basals into single 5-minute timestamps
        # For multiple basals occuring in a 5-minute period, choose the last
        # NOTE: This will result in a slight loss of accuracy of insulin
        # delivered within a 5-minute period

        # TODO: Create an algorithm to upsample basals to a 1-minute interval,
        # then downsample back to a 5-minute virtual "delivered" basal

        basal_df.sort_values('est.localTime',
                             ascending=True,
                             inplace=True)

        basal_df.drop_duplicates('rounded_local_time',
                                 keep='last',
                                 inplace=True)
        temp_basal_events['dose_values'] = basal_df['rate']
        temp_basal_events['dose_start_times'] = basal_df['rounded_local_time']
        temp_basal_events['dose_end_times'] = \
            basal_df.apply(lambda x: x['rounded_local_time'] +
                           datetime.timedelta(milliseconds=x['duration']),
                           axis=1)
        temp_basal_events['dose_types'] = 'DoseType.tempbasal'
        temp_basal_events['dose_value_units'] = 'U/hr'

    suspend_df = snapshot_df[snapshot_df.deliveryType == 'suspend'].copy()

    if len(suspend_df) > 0:
        # Merge suspends into single 5-minute timestamps
        # For multiple suspends occuring in a 5-minute period, choose the last

        suspend_df.sort_values('est.localTime',
                               ascending=True,
                               inplace=True)

        suspend_df.drop_duplicates('rounded_local_time',
                                   keep='last',
                                   inplace=True)

        suspend_events['dose_start_times'] = suspend_df['rounded_local_time']
        suspend_events['dose_values'] = 0

        suspend_events['dose_end_times'] = \
            suspend_df.apply(lambda x: x['rounded_local_time'] +
                             datetime.timedelta(milliseconds=x['duration']),
                             axis=1)
        suspend_events['dose_types'] = 'DoseType.suspend'
        suspend_events['dose_value_units'] = 'U/hr'

    dose_events = pd.concat([bolus_events,
                             extended_events,
                             temp_basal_events,
                             suspend_events], sort=False)

    dose_events['actual_doses'] = dose_events['dose_values']

    if len(dose_events) > 0:
        dose_events['dose_start_times'] = \
            dose_events['dose_start_times'].dt.strftime("%Y-%m-%d %H:%M:%S")

        dose_events['dose_end_times'] = \
            dose_events['dose_end_times'].dt.strftime("%Y-%m-%d %H:%M:%S")

    return dose_events


def interpolate_and_smooth_cgm(cgm_df,
                               condition_num,
                               add_cgm_trail,
                               evaluation_time):
    """Add 30-minute trailing cgm trace by applying the condition rate to
    evaluation point"""

    # Get the start of the condition's calculation area
    # WARNING: Avoid interpolating or backfilling data after this point
    # Else you might risk filling in gaps that were necessary in the condition
    condition_calc_start = evaluation_time - datetime.timedelta(days=1)
    before_condition = cgm_df['glucose_dates'] < condition_calc_start

    # Interpolate forward NaNs before condition area (using linear default)
    # This is to prevent the rolling average from disrupting the condition
    cgm_df.loc[before_condition,
               'glucose_values'] = cgm_df.loc[before_condition,
                                              'glucose_values'].interpolate()

    # Backfill NaNs to the start of the dataframe
    cgm_df.loc[before_condition,
               'glucose_values'] = \
        cgm_df.loc[before_condition,
                   'glucose_values'].fillna(method='backfill')

    # Use centered rolling average ± 3 points (15 min)
    cgm_rolling = cgm_df['glucose_values'].rolling(window=7,
                                                   min_periods=1,
                                                   center=True)

    cgm_df['glucose_values'] = cgm_rolling.mean().round(2)

    # Interpolate forward NaNs on entire dataframe (using linear default)
    cgm_df['glucose_values'] = cgm_df['glucose_values'].interpolate().round(1)

    # cgm_df.loc[cgm_df['glucose_values'].notnull(), 'glucose_values'] = \
    #     cgm_df.loc[cgm_df['glucose_values'].notnull(),
    #                'glucose_values'].astype(int)

    # Drop the trailing values after the evaluation point
    cgm_df = cgm_df[cgm_df.glucose_dates <= evaluation_time]

    if cgm_df.glucose_values.isnull().sum() > 0:
        print("NULL VALUES STILL IN CGM_DF!!")

    return cgm_df


def get_cgm_df(snapshot_df,
               smooth_cgm,
               condition_num,
               start_time,
               end_time,
               add_cgm_trail,
               evaluation_time):
    """Gets the CGM values from the snapshot"""

    df_columns = ['glucose_dates',
                  'glucose_values',
                  'actual_blood_glucose',
                  'glucose_units']

    cgm_df = pd.DataFrame(columns=df_columns)

    cgm_data = snapshot_df[snapshot_df.type == 'cbg'].copy()

    # first_timestamp = cgm_data["rounded_local_time"].min()
    # last_timestamp = cgm_data["rounded_local_time"].max()

    # ts_len = len(pd.date_range(first_timestamp, last_timestamp, freq="5min"))
    # print("CGM Data Length: " + str(ts_len))

    # Force cgm dataframe length to 2880
    # cgm_len = 288*10
    # if ts_len < cgm_len:
    #    delta_to_add = cgm_len - ts_len
    #    last_timestamp = \
    #        last_timestamp + datetime.timedelta(minutes=5*delta_to_add)

    contiguous_ts = pd.date_range(start_time, end_time, freq="5min")

    contiguous_df = pd.DataFrame(contiguous_ts, columns=["rounded_local_time"])

    cgm_data = pd.merge(contiguous_df,
                        cgm_data,
                        how="left",
                        on="rounded_local_time"
                        )
    # Remove CGM duplicates from the contiguous_df
    cgm_data, nRoundedTimeDuplicatesRemoved, cgmPercentDuplicated = \
        cond_finder.remove_contiguous_rounded_CGM_duplicates(cgm_data)

    # Drop cgm duplicates in snapshot (if any)
    # cgm_data.sort_values(['uploadId', 'rounded_local_time'],
    #                     ascending=True,
    #                     inplace=True)

    # cgm_data.drop_duplicates('rounded_local_time', inplace=True)

    # cgm_data.sort_values(['rounded_local_time'],
    #                     ascending=True,
    #                     inplace=True)

    cgm_df['glucose_dates'] = cgm_data.rounded_local_time
    cgm_df['glucose_values'] = round(cgm_data.value * 18.01559, 1)

    if(smooth_cgm):
        # Interpolate and smooth the data
        cgm_df = interpolate_and_smooth_cgm(cgm_df,
                                            condition_num,
                                            add_cgm_trail,
                                            evaluation_time)

    cgm_df['glucose_dates'] = \
        cgm_df['glucose_dates'].dt.strftime("%Y-%m-%d %H:%M:%S")

    cgm_df['actual_blood_glucose'] = cgm_df['glucose_values']
    cgm_df['glucose_units'] = 'mg/dL'

    return cgm_df


def get_last_temp_basal():
    """Retruns a default empty dataframe for df_last_temporary_basal"""
    df_last_temporary_basal = pd.DataFrame()
    return df_last_temporary_basal


def get_time_to_calculate_at(evaluation_time):
    """Creates the df_misc dataframe with the snapshot evaluation_time"""

    df_columns = [0]
    df_index = ['offset_applied_to_dates',
                'time_to_calculate_at']

    df_misc = pd.DataFrame(index=df_index,
                           columns=df_columns)

    df_misc.loc['offset_applied_to_dates'] = 0

    # Get time to calculate at
    time_to_calculate_at = evaluation_time.strftime("%Y-%m-%d %H:%M:%S")
    df_misc.loc['time_to_calculate_at'] = time_to_calculate_at

    return df_misc


def get_settings(birthdate,
                 diagnosis_date,
                 evaluation_time,
                 basal_rates):
    """Provides a default settings dataframe"""

    df_columns = ['settings']
    df_index = ['age',
                'ylw',
                'model',
                'momentum_data_interval',
                'suspend_threshold',
                'dynamic_carb_absorption_enabled',
                'retrospective_correction_integration_interval',
                'recency_interval',
                'retrospective_correction_grouping_interval',
                'rate_rounder',
                'insulin_delay',
                'carb_delay',
                'default_absorption_times',
                'max_basal_rate',
                'max_bolus',
                'retrospective_correction_enabled']

    df_settings = pd.DataFrame(index=df_index,
                               columns=df_columns)

    # Calculate age and ylw
    if type(birthdate) == float:
        age = '-1'
    else:
        birthdate = pd.to_datetime(birthdate, utc=True)

        if birthdate.year > datetime.datetime.now().year:
            birthdate = birthdate.replace(year=birthdate.year-100)

        age = \
            int(np.floor((evaluation_time - birthdate).days/365))

    if type(diagnosis_date) == float:
        ylw = '-1'
    else:
        diagnosis_date = pd.to_datetime(diagnosis_date, utc=True)

        if diagnosis_date.year > datetime.datetime.now().year:
            diagnosis_date = \
                diagnosis_date.replace(year=diagnosis_date.year-100)

        ylw = \
            int(np.floor((evaluation_time - diagnosis_date).days/365))

    # Create default df_settings
    df_settings.loc['age'] = age
    df_settings.loc['ylw'] = ylw
    df_settings.loc['model'] = '[360.0, 65]'
    if age < 13:
        df_settings.loc['model'] = '[360.0, 55]'
    df_settings.loc['momentum_data_interval'] = '15'
    df_settings.loc['suspend_threshold'] = '70'
    df_settings.loc['dynamic_carb_absorption_enabled'] = 'TRUE'
    df_settings.loc['retrospective_correction_integration_interval'] = '30'
    df_settings.loc['recency_interval'] = '15'
    df_settings.loc['retrospective_correction_grouping_interval'] = '30'
    df_settings.loc['rate_rounder'] = '0.05'
    df_settings.loc['insulin_delay'] = '10'
    df_settings.loc['carb_delay'] = '10'
    df_settings.loc['default_absorption_times'] = '[120.0, 180.0, 240.0]'

    max_sched_basal_rate = basal_rates['actual_basal_rates'].max()
    df_settings.loc['max_basal_rate'] = str(max_sched_basal_rate * 3)
    df_settings.loc['max_bolus'] = '20'
    df_settings.loc['retrospective_correction_enabled'] = 'TRUE'

    return df_settings


def get_simple_settings(basal_rates,
                        carb_ratios,
                        isfs,
                        df_target_range):

    # Get the weighted average basal_rates
    simple_basal_rate = pd.DataFrame(columns=basal_rates.columns, index=[0])

    weighted_avg_basal_rate = (
        np.sum(
            basal_rates["basal_rate_minutes"]
            * basal_rates["actual_basal_rates"]
        )
        / basal_rates["basal_rate_minutes"].sum()
    )

    # Round to nearest 0.05 U/hr
    weighted_avg_basal_rate = (
        round(round(weighted_avg_basal_rate/0.05)*0.05, 2)
    )

    simple_basal_rate.loc[0, :] = (
        datetime.time(0, 0).strftime('%H:%M:%S'),
        60*24,
        weighted_avg_basal_rate,
        weighted_avg_basal_rate,
        "U/hr"
    )

    # Get average carb ratio
    simple_carb_ratio = pd.DataFrame(columns=carb_ratios.columns, index=[0])

    average_cir = carb_ratios["carb_ratio_values"].mean().round().astype(int)

    simple_carb_ratio.loc[0, :] = (
        datetime.time(0, 0).strftime('%H:%M:%S'),
        average_cir,
        average_cir,
        "g/U"
    )

    # Get average isf
    simple_isf = pd.DataFrame(columns=isfs.columns, index=[0])

    average_isf = isfs["sensitivity_ratio_values"].mean().round().astype(int)

    simple_isf.loc[0, :] = (
        datetime.time(0, 0).strftime('%H:%M:%S'),
        datetime.time(0, 0).strftime('%H:%M:%S'),
        average_isf,
        average_isf,
        "mg/dL/U"
    )

    # Set bg targets to 100-120
    simple_targets = pd.DataFrame(columns=df_target_range.columns, index=[0])

    simple_targets.loc[0, :] = (
        datetime.time(0, 0).strftime('%H:%M:%S'),
        datetime.time(0, 0).strftime('%H:%M:%S'),
        100,
        120,
        "mg/dL"
    )

    return simple_basal_rate, simple_carb_ratio, simple_isf, simple_targets


def create_empty_events(carb_events,
                        dose_events,
                        df_misc):

    time_to_calculate_at = df_misc.loc['time_to_calculate_at', 0]

    # Create empty carb event
    empty_carb_event = pd.DataFrame(columns=carb_events.columns, index=[0])
    empty_carb_event.loc[0, :] = (
        time_to_calculate_at,
        0,
        0,
        180,
        "g"
    )

    # Create empty dose event
    empty_dose_event = pd.DataFrame(columns=dose_events.columns, index=[0])
    empty_dose_event.loc[0, :] = (
        "DoseType.bolus",
        time_to_calculate_at,
        time_to_calculate_at,
        0,
        0,
        "U"
    )

    return empty_carb_event, empty_dose_event


def get_snapshot(data,
                 file_name,
                 evaluation_time,
                 birthdate,
                 diagnosis_date,
                 smooth_cgm,
                 simplify_settings,
                 empty_events,
                 condition_num,
                 add_cgm_trail):
    """Main function wrapper to assemble snapshot dataframes"""

    # Start by getting the 48-hour window ± 24hrs around the evaluation point
    # evaluation_index = data.index[data.id == evaluation_point_loc]

    data["rounded_local_time"] = \
        pd.to_datetime(data["est.localTime"],
                       utc=True).dt.ceil(freq="5min")

    # evaluation_time = \
    #    pd.to_datetime(data.loc[evaluation_index,
    #                            'rounded_local_time'].values[0],
    #                   utc=True)

    df_misc = get_time_to_calculate_at(evaluation_time)

    # Start time is evaluation_time - 10 days with a non-inclusive first value,
    # add 5 minutes to offset to a timestamp of 9 days, 23 hours, 55 minutes
    start_time = evaluation_time - datetime.timedelta(days=9,
                                                      hours=23,
                                                      minutes=55)

    end_time = evaluation_time + datetime.timedelta(minutes=15)

    snapshot_df = data[(data['rounded_local_time'] >= start_time) &
                       (data['rounded_local_time'] <= end_time)]

    # Get pumpSettings list of active schedules
    active_schedule = get_active_schedule(data,
                                          snapshot_df,
                                          file_name,
                                          evaluation_time)

    # Drop unused columns that may have been used in other schedule types
    active_schedule = active_schedule.dropna(axis=1).reset_index(drop=True)

    # schedule_distance = \
    #    int((active_schedule.rounded_local_time -
    #         evaluation_time).values[0])/1e9/60/60/24

    # Get entire dataframe's bolus and basal entries as a last effort
    # to manually extract pump settings if not available
    bolus_df = data[data.type == 'bolus'].copy()
    basal_df = data[data.type == 'basal'].copy()

    basal_rates = get_basal_rates(active_schedule, basal_df)
    carb_ratios = get_carb_ratios(active_schedule, bolus_df)
    isfs = get_isfs(active_schedule, bolus_df)
    df_target_range = get_target_ranges(active_schedule, bolus_df)

    carb_events = get_carb_events(snapshot_df)
    dose_events = get_dose_events(snapshot_df)
    cgm_df = get_cgm_df(snapshot_df,
                        smooth_cgm,
                        condition_num,
                        start_time,
                        end_time,
                        add_cgm_trail,
                        evaluation_time)

    df_last_temporary_basal = get_last_temp_basal()

    if(simplify_settings):
        (basal_rates,
         carb_ratios,
         isfs,
         df_target_range) = get_simple_settings(basal_rates,
                                                carb_ratios,
                                                isfs,
                                                df_target_range)

    df_settings = get_settings(birthdate,
                               diagnosis_date,
                               evaluation_time,
                               basal_rates)

    if(empty_events):
        carb_events, dose_events = create_empty_events(carb_events,
                                                       dose_events,
                                                       df_misc)

    return (basal_rates, carb_events, carb_ratios, dose_events, cgm_df,
            df_last_temporary_basal, df_misc, isfs,
            df_settings, df_target_range
            )


def dataframe_inputs_to_dict(dfs, df_misc, df_settings):
    """Function from pyLoopKit's input_data_tools.py
    write the dataframes back to one dictionary
    """
    input_dictionary = dict()
    input_dictionary = df_misc.to_dict()[0]
    for df in dfs:
        for col in df.columns:
            if "units" not in col:
                input_dictionary[col] = df[col].tolist()
            else:
                input_dictionary[col] = df[col].unique()[0]

    input_dictionary["settings_dictionary"] = df_settings.to_dict()["settings"]

    # set the format back for the edge cases
    input_dictionary["settings_dictionary"]["model"] = np.safe_eval(
        input_dictionary["settings_dictionary"]["model"]
    )
    input_dictionary["settings_dictionary"]["default_absorption_times"] = (
        np.safe_eval(
            input_dictionary["settings_dictionary"]["default_absorption_times"]
        )
    )

    input_dictionary["offset_applied_to_dates"] = (
        int(input_dictionary["offset_applied_to_dates"])
    )

    return input_dictionary


def combine_into_one_dataframe(snapshot):
    """Function from pyLoopKit's input_data_tools.py
    Combines the dataframes into one big dataframe,
    put glucose at end since that trace is typically long
    """
    (
        df_basal_rate, df_carb, df_carb_ratio, df_dose, df_glucose,
        df_last_temporary_basal, df_misc, df_sensitivity_ratio,
        df_settings, df_target_range
    ) = snapshot

    combined_df = pd.DataFrame()
    combined_df = pd.concat([combined_df, df_settings], sort=False)
    combined_df = pd.concat([combined_df, df_misc], sort=False)

    dfs = [
       df_basal_rate, df_carb, df_carb_ratio, df_dose,
       df_last_temporary_basal, df_sensitivity_ratio,
       df_target_range, df_glucose
    ]

    for df in dfs:
        df.reset_index(drop=True, inplace=True)
        combined_df = pd.concat([combined_df, df.T], sort=False)

    # move settings back to the front of the dataframe
    combined_df = combined_df[np.append("settings", combined_df.columns[0:-1])]
    combined_df = \
        combined_df.reset_index().rename(columns={'index': 'setting_name'})

    return combined_df


def export_snapshot(snapshot,
                    file_name,
                    condition_num,
                    export_folder):
    """Exports the snapshot (10-element tuple) into a pickle file"""

    if not os.path.exists(export_folder):
        os.makedirs(export_folder)

    export_filename = file_name + "_condition" + str(condition_num) + ".csv"
    export_path = export_folder + "/" + export_filename

    combined_df = combine_into_one_dataframe(snapshot)
    combined_df.to_csv(export_path, index=False)

    print("Successfully completed: " + export_filename)

    return


def get_settings_summary(file_name,
                         condition_num,
                         snapshot,
                         condition_check):
    """Get a table of settings to be used in a cumulative summary file"""

    summary_columns = ['file_name',
                       'condition_num',
                       'condition_check',
                       'age',
                       'ylw',
                       'CIR',
                       'ISF',
                       'BR']

    settings_summary = pd.DataFrame(index=[0], columns=summary_columns)

    settings_summary['file_name'] = file_name
    settings_summary['condition_num'] = condition_num
    settings_summary['condition_check'] = condition_check
    settings_summary['age'] = snapshot[8].loc['age']['settings']
    settings_summary['ylw'] = snapshot[8].loc['ylw']['settings']
    settings_summary['CIR'] = snapshot[2]['actual_carb_ratios'][0]
    settings_summary['ISF'] = snapshot[7]['actual_sensitivity_ratios'][0]
    settings_summary['BR'] = snapshot[0]['actual_basal_rates'][0]

    return settings_summary


def validate_condition(snapshot,
                       condition_num,
                       contiguous_df,
                       evaluation_time):
    """Validate the snapshot cgm data condition with the expected condition"""

    cgm_df = snapshot[4].copy()
    cgm_df["rounded_local_time"] = \
        pd.to_datetime(cgm_df["glucose_dates"], utc=True)
    cgm_df["value"] = cgm_df["glucose_values"]
    cgm_df = cond_finder.rolling_30min_median(cgm_df)
    cgm_df = cond_finder.rolling_15min_slope(cgm_df)
    cgm_df = cond_finder.label_conditions(cgm_df)

    condition_start = evaluation_time - datetime.timedelta(minutes=30)
    condition_end = evaluation_time

    original_values = \
        contiguous_df.loc[
            (contiguous_df['rounded_local_time'] > condition_start) &
            (contiguous_df['rounded_local_time'] <= condition_end),
            "value"].values

    new_values = \
        cgm_df.loc[
            (cgm_df['rounded_local_time'] > condition_start) &
            (cgm_df['rounded_local_time'] <= condition_end),
            "value"].values

    original_eval = \
        contiguous_df[contiguous_df['rounded_local_time'] == evaluation_time]

    original_median = original_eval['rolling_30min_median']
    original_rate = original_eval['rolling_15min_slope']
    original_condition = original_eval['condition'].values[0]

    new_eval = cgm_df.loc[cgm_df['rounded_local_time'] == evaluation_time]

    new_median = new_eval['rolling_30min_median']
    new_rate = new_eval['rolling_15min_slope']
    new_condition = new_eval['condition'].values[0]

    if any(original_values != new_values):
        print("\nOriginal and new cgm values are different!\n")

    condition_check = (original_condition == new_condition == condition_num)

    return condition_check


# %%
if __name__ == "__main__":

    start_time = time.time()

    # Import results from batch-icgm-condition-stats
    condition_file = "PHI-batch-icgm-condition-stats-2020-02-27-with-metadata.csv"
    condition_df = pd.read_csv(condition_file, low_memory=False)

    # Snapshot processing parameters
    simplify_settings = True
    empty_events = True
    smooth_cgm = True
    add_cgm_trail = False

    settings_summaries = []

    for file_selection in range(int(len(condition_df))):
        #file_selection = 1
        print("STARTING FILE #: " + str(file_selection))
        file_name = condition_df.loc[file_selection, 'file_name']

        # Get birthdate/diagnosis_date metadata for each person
        birthdate = condition_df.loc[file_selection, 'birthday']
        diagnosis_date = condition_df.loc[file_selection, 'diagnosisDate']

        # Location of csvs
    data_location = "train-data/"
        file_path = os.path.join(data_location, file_name)
        data = pd.read_csv(file_path, low_memory=False)
        data = cond_finder.add_uploadDateTime(data)

        (contiguous_df,
         nRoundedTimeDuplicatesRemoved,
         cgmPercentDuplicated
         ) = cond_finder.create_5min_contiguous_df(data)

        # Calculate the median BG with a 30-minute rolling window
        contiguous_df = \
            cond_finder.rolling_30min_median(contiguous_df)

        # Calculate the slope in mg/dL/min with a 15-minute rolling window
        contiguous_df = \
            cond_finder.rolling_15min_slope(contiguous_df)

        # Apply one of the 9 conditions labels to each CGM point
        contiguous_df = \
            cond_finder.label_conditions(contiguous_df)

        # Loop through each condition, calculate, and export the snapshot
        for condition_num in range(1, 10):
            condition_col = 'cond' + str(condition_num) + '_eval_time'
            evaluation_time = condition_df.loc[file_selection,
                                               condition_col]

            if not pd.isnull(evaluation_time):
                evaluation_time = pd.to_datetime(evaluation_time, utc=True)

                snapshot = get_snapshot(data,
                                        file_name,
                                        evaluation_time,
                                        birthdate,
                                        diagnosis_date,
                                        smooth_cgm,
                                        simplify_settings,
                                        empty_events,
                                        condition_num,
                                        add_cgm_trail
                                        )

                condition_check = \
                    validate_condition(snapshot,
                                       condition_num,
                                       contiguous_df,
                                       evaluation_time)

                settings_summary = get_settings_summary(file_name,
                                                        condition_num,
                                                        snapshot,
                                                        condition_check)

                settings_summaries.append(settings_summary)

                export_folder = "snapshot_export"

                export_snapshot(snapshot,
                                file_name,
                                condition_num,
                                export_folder)

    # Create settings summaries for export
    settings_summaries = pd.concat(settings_summaries).reset_index(drop=True)
    today_timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
    settings_summary_export_filename = \
        'snapshot-processor-settings-summary-table-' + \
        today_timestamp + \
        '.csv'

    settings_summaries.to_csv(settings_summary_export_filename, index=False)

    end_time = time.time()
    elapsed_minutes = (end_time - start_time)/60
    elapsed_time_message = "Processed all snapshots in: " + \
        str(elapsed_minutes) + " minutes\n"
    print(elapsed_time_message)
