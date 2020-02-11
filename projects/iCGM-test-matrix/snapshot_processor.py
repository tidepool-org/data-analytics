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
import pickle
import numpy as np
import datetime
import ast
import os
# %% Functions


def get_active_schedules(data,
                         snapshot_df,
                         file_name,
                         evaluation_point_loc,
                         evaluation_time):
    """Get the pumpSettinsg row of active schedules used during the snapshot"""

    # Get all schedules and their upload ids
    schedules = data[data.activeSchedule.notnull()]

    # Check which schedule matches the active pump upload during the snapshot
    active_schedules = \
        schedules[schedules.uploadId.isin(snapshot_df.uploadId)]

    # If more than one active schedule, pick the one closest to the time of
    # the evaluation point
    if(len(active_schedules) > 1):
        print(file_name +
              " - " +
              evaluation_point_loc +
              " MULTIPLE ACTIVE SCHEDULES IN ONE SNAPSHOT!")

        nearest_uploadid = \
            snapshot_df.loc[((snapshot_df.type == 'bolus') |
                            (snapshot_df.type == 'basal')) &
                            (snapshot_df.time < evaluation_time),
                            'uploadId'].values[-1]

        active_schedules = \
            active_schedules[active_schedules.uploadId == nearest_uploadid]

    # If no active schedule is assigned during an upload, pick the one closest
    # to the time of the evaluation point
    if len(active_schedules) == 0:
        nearest_schedule_time = \
            schedules.loc[schedules.time < evaluation_time, 'time'].max()
        active_schedules = \
            schedules[schedules.time == nearest_schedule_time]

    return active_schedules


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


def get_basal_rates(active_schedules):
    """Get the basal rates from the active schedule"""
    df_columns = ['basal_rate_start_times',
                  'basal_rate_minutes',
                  'basal_rate_values',
                  'actual_basal_rates',
                  'basal_rate_units']

    basal_rates = pd.DataFrame(columns=df_columns)

    basal_schedules = \
        ast.literal_eval(active_schedules.basalSchedules.values[0])

    active_name = active_schedules.activeSchedule.values[0]
    active_basal_rates = basal_schedules.get(active_name)

    start_times = []
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


def get_carb_ratios(active_schedules):
    """Get the carb to insulin ratio(s) from the active schedule"""

    df_columns = ['carb_ratio_start_times',
                  'carb_ratio_values',
                  'actual_carb_ratios',
                  'carb_ratio_value_units']

    carb_ratios = pd.DataFrame(columns=df_columns)

    if 'carbRatios' in active_schedules:
        carb_ratio_schedules = \
            ast.literal_eval(active_schedules.carbRatios.values[0])
        active_name = active_schedules.activeSchedule.values[0]
        active_carb_ratios = carb_ratio_schedules.get(active_name)
    elif 'carbRatio' in active_schedules:
        active_carb_ratios = \
            ast.literal_eval(active_schedules.carbRatio.values[0])
    else:
        print("NO CARB RATIOS!")

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


def get_isfs(active_schedules):
    """Get the insulin sensitivity ratio(s) from the active schedule"""

    df_columns = ['sensitivity_ratio_start_times',
                  'sensitivity_ratio_end_times',
                  'sensitivity_ratio_values',
                  'actual_sensitivity_ratios',
                  'sensitivity_ratio_value_units']

    isfs = pd.DataFrame(columns=df_columns)

    if 'insulinSensitivities' in active_schedules:
        isf_schedules = \
            ast.literal_eval(active_schedules.insulinSensitivities.values[0])
        active_name = active_schedules.activeSchedule.values[0]
        active_isfs = isf_schedules.get(active_name)
    elif 'insulinSensitivity' in active_schedules:
        active_isfs = \
            ast.literal_eval(active_schedules.insulinSensitivity.values[0])
    else:
        print("NO ISFS FOUND!")

    start_times = []

    for isf_loc in range(len(active_isfs)):
        isf_info = active_isfs[isf_loc]
        isf = round(isf_info.get('amount')*18.01559)
        start_time = isf_info.get('start')
        start_string = get_relative_timestamp(start_time)
        start_times.append(start_string)

        isfs.loc[isf_loc, 'sensitivity_ratio_start_times'] = start_string
        isfs.loc[isf_loc, 'sensitivity_ratio_values'] = isf

    isfs['actual_sensitivity_ratios'] = isfs['sensitivity_ratio_values']
    isfs['sensitivity_ratio_value_units'] = 'mg/dL/U'

    # Shift start times by -1 to form the end times
    end_times = start_times[1:] + [start_times[0]]
    isfs['sensitivity_ratio_end_times'] = end_times

    return isfs


def get_target_ranges(active_schedules):
    """Get the target BG ranges from the active schedule"""

    df_columns = ['target_range_start_times',
                  'target_range_end_times',
                  'target_range_minimum_values',
                  'target_range_maximum_values',
                  'target_range_value_units']

    df_target_range = pd.DataFrame(columns=df_columns)

    if 'bgTargets' in active_schedules:
        target_schedules = \
            ast.literal_eval(active_schedules.bgTargets.values[0])

        active_name = active_schedules.activeSchedule.values[0]
        active_targets = target_schedules.get(active_name)
    elif 'bgTarget' in active_schedules:
        active_targets = ast.literal_eval(active_schedules.bgTarget.values[0])
    elif 'bgTarget.start' in active_schedules:
        target_start = int(active_schedules['bgTarget.start'].values)
        active_targets = dict({'start': target_start})

        if 'bgTarget.target' in active_schedules:
            bg_target = float(active_schedules['bgTarget.target'].values)
            active_targets.update({'target': bg_target})

        if 'bgTarget.range' in active_schedules:
            target_range = float(active_schedules['bgTarget.range'].values)
            active_targets.update({'range': target_range})

        if 'bgTarget.high' in active_schedules:
            target_high = float(active_schedules['bgTarget.high'].values)
            active_targets.update({'high': target_high})

        if 'bgTarget.low' in active_schedules:
            target_low = float(active_schedules['bgTarget.low'].values)
            active_targets.update({'low': target_low})

        active_targets = [active_targets]

    else:
        print("NO TARGET RANGES!")

    start_times = []

    for target_loc in range(len(active_targets)):
        target_info = active_targets[target_loc]
        start_time = target_info.get('start')
        start_string = get_relative_timestamp(start_time)
        start_times.append(start_string)

        df_target_range.loc[target_loc,
                            'target_range_start_times'] = start_string
        target = round(target_info.get('target')*18.01559)
        df_target_range.loc[target_loc, 'target_range_minimum_values'] = target
        df_target_range.loc[target_loc, 'target_range_maximum_values'] = target

        if 'range' in target_info.keys():
            target_range = round(target_info.get('range')*18.01559)
            df_target_range.loc[target_loc, 'target_range_minimum_values'] = \
                target - target_range

            df_target_range.loc[target_loc, 'target_range_maximum_values'] = \
                target + target_range

        if 'high' in target_info.keys():
            target_high = round(target_info.get('high')*18.01559)
            df_target_range.loc[target_loc,
                                'target_range_maximum_values'] = target_high

        if 'low' in target_info.keys():
            target_low = round(target_info.get('high')*18.01559)
            df_target_range.loc[target_loc,
                                'target_range_minimum_values'] = target_low

    df_target_range['target_range_value_units'] = 'mg/dL'

    # Shift start times by -1 to form the end times
    end_times = start_times[1:] + [start_times[0]]
    df_target_range['target_range_end_times'] = end_times

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

    carb_events['carb_dates'] = carb_df.time.dt.strftime("%Y-%m-%d %H:%M:%S")
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

    bolus_df = snapshot_df[snapshot_df.type == 'bolus']

    if len(bolus_df) > 0:
        bolus_events['dose_values'] = bolus_df['normal']
        bolus_events['dose_start_times'] = bolus_df['time']
        bolus_events['dose_end_times'] = bolus_df['time']
        bolus_events['dose_types'] = 'DoseType.bolus'
        bolus_events['dose_value_units'] = 'U'

    extended_df = bolus_df[bolus_df.extended > 0]

    if len(extended_df) > 0:
        extended_df = bolus_df[bolus_df.subType == 'dual/square']

        extended_events['dose_values'] = extended_df['extended']
        extended_events['dose_start_times'] = extended_df['time']
        extended_events['dose_end_times'] = \
            extended_df.apply(lambda x: x['time'] +
                              datetime.timedelta(milliseconds=x['duration']),
                              axis=1)
        extended_events['dose_types'] = 'DoseType.extended'
        extended_events['dose_value_units'] = 'U'

    basal_df = snapshot_df[snapshot_df.deliveryType == 'temp']

    if len(basal_df) > 0:
        temp_basal_events['dose_values'] = basal_df['rate']
        temp_basal_events['dose_start_times'] = basal_df['time']
        temp_basal_events['dose_end_times'] = \
            basal_df.apply(lambda x: x['time'] +
                           datetime.timedelta(milliseconds=x['duration']),
                           axis=1)
        temp_basal_events['dose_types'] = 'DoseType.tempbasal'
        temp_basal_events['dose_value_units'] = 'U/hr'

    suspend_df = snapshot_df[snapshot_df.deliveryType == 'suspend']

    if len(suspend_df) > 0:
        suspend_events['dose_start_times'] = suspend_df['time']
        suspend_events['dose_values'] = 0

        suspend_events['dose_end_times'] = \
            suspend_df.apply(lambda x: x['time'] +
                             datetime.timedelta(milliseconds=x['duration']),
                             axis=1)
        suspend_events['dose_types'] = 'DoseType.suspend'
        suspend_events['dose_value_units'] = 'U/hr'

    dose_events = pd.concat([bolus_events,
                             extended_events,
                             temp_basal_events,
                             suspend_events])

    dose_events['actual_doses'] = dose_events['dose_values']

    if len(dose_events) > 0:
        dose_events['dose_start_times'] = \
            dose_events['dose_start_times'].dt.strftime("%Y-%m-%d %H:%M:%S")

        dose_events['dose_end_times'] = \
            dose_events['dose_end_times'].dt.strftime("%Y-%m-%d %H:%M:%S")

    return dose_events


def get_cgm_df(snapshot_df):
    """Gets the CGM values from the snapshot"""

    df_columns = ['glucose_dates',
                  'glucose_values',
                  'actual_blood_glucose',
                  'glucose_units']

    cgm_df = pd.DataFrame(columns=df_columns)

    cgm_data = snapshot_df[snapshot_df.type == 'cbg']
    cgm_df['glucose_dates'] = cgm_data.time.dt.strftime("%Y-%m-%d %H:%M:%S")
    cgm_df['glucose_values'] = round(cgm_data.value * 18.01559)
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


def get_settings():
    """Provides a default settings dataframe"""

    df_columns = ['settings']
    df_index = ['model',
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

    # Create default df_settings

    df_settings.loc['model'] = [[360.0, 65]]
    df_settings.loc['momentum_data_interval'] = 15
    df_settings.loc['suspend_threshold'] = 70
    df_settings.loc['dynamic_carb_absorption_enabled'] = True
    df_settings.loc['retrospective_correction_integration_interval'] = 30
    df_settings.loc['recency_interval'] = 15
    df_settings.loc['retrospective_correction_grouping_interval'] = 30
    df_settings.loc['rate_rounder'] = 0.05
    df_settings.loc['insulin_delay'] = 10
    df_settings.loc['carb_delay'] = 10
    df_settings.loc['default_absorption_times'] = [[120.0, 180.0, 240.0]]
    df_settings.loc['max_basal_rate'] = 35
    df_settings.loc['max_bolus'] = 30
    df_settings.loc['retrospective_correction_enabled'] = True

    return df_settings


def get_snapshot(data,
                 file_name,
                 evaluation_point_loc):

    """Main function wrapper to assemble snapshot dataframes"""

    # Start by getting the 48-hour window ± 24hrs around the evaluation point
    evaluation_index = data.index[data.id == evaluation_point_loc]

    data['time'] = pd.to_datetime(data['time'], utc=True)
    evaluation_time = pd.to_datetime(data.time[evaluation_index].values[0],
                                     utc=True)

    df_misc = get_time_to_calculate_at(evaluation_time)

    start_time = evaluation_time - datetime.timedelta(days=1)
    end_time = evaluation_time + datetime.timedelta(days=1)

    snapshot_df = data[(data.time >= start_time) & (data.time <= end_time)]

    # Get pumpSettings list of active schedules
    active_schedules = get_active_schedules(data,
                                            snapshot_df,
                                            file_name,
                                            evaluation_point_loc,
                                            evaluation_time)

    active_schedules = active_schedules.dropna(axis=1)

    basal_rates = get_basal_rates(active_schedules)
    carb_ratios = get_carb_ratios(active_schedules)
    isfs = get_isfs(active_schedules)
    df_target_range = get_target_ranges(active_schedules)

    carb_events = get_carb_events(snapshot_df)
    dose_events = get_dose_events(snapshot_df)
    cgm_df = get_cgm_df(snapshot_df)

    df_last_temporary_basal = get_last_temp_basal()
    df_settings = get_settings()

    return (basal_rates, carb_events, carb_ratios, dose_events, cgm_df,
            df_last_temporary_basal, df_misc, isfs,
            df_settings, df_target_range
            )


def export_snapshot(snapshot,
                    file_name,
                    condition_num,
                    export_folder):
    """Exports the snapshot (10-element tuple) into a pickle file"""

    if not os.path.exists(export_folder):
        os.makedirs(export_folder)

    export_filename = file_name + "_" + str(condition_num) + ".pkl"
    export_path = export_folder + "/" + export_filename

    with open(export_path, 'wb') as pickle_file:
        pickle.dump(snapshot, pickle_file)

    print("Successfully completed: " + export_filename)

    return


# %%
if __name__ == "__main__":

    # Import results from batch-icgm-condition-stats
    condition_file = "PHI-batch-icgm-condition-stats-2020-01-31.csv"
    condition_df = pd.read_csv(condition_file, low_memory=False)

    file_selection = 1
    file_name = condition_df.loc[file_selection, 'file_name']

    # Location of csvs
    data_location = "train-data/"
    file_path = os.path.join(data_location, file_name)
    data = pd.read_csv(file_path, low_memory=False)

    # Loop through each condition, calculate, and export the snapshot
    for condition_num in range(1, 10):
        condition_col = 'cond' + str(condition_num) + '_eval_loc'
        evaluation_point_loc = condition_df.loc[file_selection, condition_col]

        snapshot = get_snapshot(data, file_name, evaluation_point_loc)

        export_folder = "snapshot_export"

        export_snapshot(snapshot,
                        file_name,
                        condition_num,
                        export_folder)
