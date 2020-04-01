#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Normalized Data Sample Generator
================================
:File: normalized-data-sample-generator.py
:Description: A generator of sample data in the normalized format that may be
used by the Tidepool Data Science Team
:Version: 0.0.1
:Created: 2020-03-02
:Authors: Jason Meno (jameno)
:Dependencies:
    * None
:License: BSD-2-Clause
"""

# %% Libraries

import pandas as pd
import numpy as np
import datetime
# %% Functions


def create_dataframe_template():
    """Creates a template of columns to be used by the data generator"""

    df_columns = [
        'timeUTC',
        'timeLocal',
        'bgValueCGM',
        'bgValueSMBG',
        'bgValueCalibration',
        'bgValuePumpCalculator',
        'insulinDeliveredTotal',
        'insulinDeliveredBasal',
        'insulinDeliveredBolus',
        'insulinDeliveredExtended',
        'carbIntake',
        'exerciseStatus',
        'exerciseName',
        'exerciseDuration',
        'exerciseDistance',
        'exerciseEnergy',
        'basalRate',
        'basalDuration',
        'basalType',
        'alarmCGMStatus',
        'alarmCGMType',
        'alarmPumpStatus',
        'alarmPumpType',
        'settingsPumpBGTarget',
        'settingsPumpInsulinSensitivity',
        'settingsPumpCarbRatio',
    ]

    template_df = pd.DataFrame(columns=df_columns)

    return template_df


def add_time_data(sample_dataset, days_of_data):
    """Adds contiguously rounded time range to dataset columns:
        * timeUTC
        * timeLocal
        * timeDevice
    """

    start_time = pd.to_datetime("2015-01-01", utc=True)
    end_time = start_time + datetime.timedelta(days=days_of_data)

    contiguous_ts = pd.date_range(start_time, end_time, freq="5min")
    local_ts = contiguous_ts.tz_convert('US/Pacific')

    sample_dataset['timeUTC'] = contiguous_ts.strftime('%Y-%m-%dT%H:%M:%S')
    sample_dataset['timeLocal'] = local_ts.strftime('%Y-%m-%dT%H:%M:%S')

    return sample_dataset


def add_bgValue_data(sample_dataset, days_of_data):
    """Adds bgValue data to dataset columns:
        * bgValueCGM
        * bgValueSMBG
        * bgValueCalibration
        * bgValuePumpCalculator
    """

    sample_dataset['bgValueCGM'] = 100

    smbg_samples = days_of_data*3
    smbg_indices = np.random.choice(
            sample_dataset.index,
            smbg_samples,
            replace=False
    )
    sample_dataset.loc[smbg_indices, 'bgValueSMBG'] = (
        sample_dataset.loc[smbg_indices, 'bgValueCGM']
    )

    calib_samples = days_of_data
    calib_indices = np.random.choice(
            sample_dataset.index,
            calib_samples,
            replace=False
    )
    sample_dataset.loc[calib_indices, 'bgValueCalibration'] = (
        sample_dataset.loc[calib_indices, 'bgValueCGM']
    )

    pump_samples = days_of_data*3
    pump_indices = np.random.choice(
            sample_dataset.index,
            pump_samples,
            replace=False
    )
    sample_dataset.loc[pump_indices, 'bgValuePumpCalculator'] = (
        sample_dataset.loc[pump_indices, 'bgValueCGM']
    )

    return sample_dataset


def add_insulin_data(sample_dataset, days_of_data):
    """Adds insulin data to dataset to dataset columns:
        * insulinDeliveredTotal
        * insulinDeliveredBasal
        * insulinDeliveredBolus
        * insulinDeliveredExtended
    """

    # Add Correction Bolus Data
    bolus_samples = days_of_data*2
    boluses = np.random.uniform(1, 20, bolus_samples)
    boluses = np.round(np.round(boluses/0.05)*0.05, 2)
    bolus_indices = np.random.choice(
            sample_dataset.index,
            bolus_samples,
            replace=False
    )
    sample_dataset.loc[bolus_indices, 'insulinDeliveredBolus'] = (
        boluses
    )

    # Add Meal Bolus data from carbIntake
    carb_indices = sample_dataset['carbIntake'].notnull()
    cir = sample_dataset.loc[carb_indices, 'settingsPumpCarbRatio']
    carbs = sample_dataset.loc[carb_indices, 'carbIntake']
    meal_boluses = np.round(np.round((carbs/cir).astype(float)/0.05)*0.05, 2)
    sample_dataset.loc[carb_indices, 'insulinDeliveredBolus'] = meal_boluses

    # Add Extended Bolus Data
    extended_samples = days_of_data//2
    extended_boluses = np.random.uniform(0.1, 1.5, extended_samples).round(2)
    extended_indices = np.random.choice(
            bolus_indices,
            extended_samples,
            replace=False
    )
    sample_dataset.loc[extended_indices, 'insulinDeliveredExtended'] = (
        extended_boluses
    )
    sample_dataset['insulinDeliveredExtended'].ffill(limit=23, inplace=True)
    sample_dataset['insulinDeliveredExtended'] = (
        round(round(sample_dataset['insulinDeliveredExtended']/0.05)*0.05, 2)
    )

    # Add Basal Data
    sample_dataset['insulinDeliveredBasal'] = sample_dataset['basalRate']/12
    sample_dataset['insulinDeliveredBasal'] = (
            round(round(sample_dataset['insulinDeliveredBasal']/0.05)*0.05, 2)
    )

    # Calculate Total Insulin
    sample_dataset['insulinDeliveredTotal'] = (
            sample_dataset[
                    ['insulinDeliveredBasal',
                     'insulinDeliveredBolus',
                     'insulinDeliveredExtended'
                     ]
            ].sum(axis=1)
    )

    return sample_dataset


def add_carb_data(sample_dataset, days_of_data):
    """Adds carb data to dataset to dataset columns:
        * carbIntake
    """

    carb_samples = days_of_data*3
    carbs = np.random.randint(1, 120, carb_samples)
    carb_indices = np.random.choice(
            sample_dataset.index,
            carb_samples,
            replace=False
    )
    sample_dataset.loc[carb_indices, 'carbIntake'] = carbs

    return sample_dataset


def add_exercise_data(sample_dataset, days_of_data):
    """Adds exercise data to dataset to dataset columns:
        * exerciseStatus
        * exerciseName
        * exerciseDuration
        * exerciseDistance
        * exerciseEnergy
    """

    exercise_samples = days_of_data//2
    duration = 60

    exercise_indices = np.random.choice(
            sample_dataset.index,
            exercise_samples,
            replace=False
    )
    sample_dataset.loc[exercise_indices, 'exerciseStatus'] = "exercising"
    sample_dataset.loc[exercise_indices, 'exerciseDuration'] = duration
    sample_dataset.loc[exercise_indices, 'exerciseName'] = "Walking"
    sample_dataset.loc[exercise_indices, 'exerciseDistance'] = "5 Miles"
    sample_dataset.loc[exercise_indices, 'exerciseEnergy'] = "315 kcal"

    sample_dataset['exerciseStatus'].ffill(limit=duration//5 - 1, inplace=True)

    return sample_dataset


def add_basal_data(sample_dataset, days_of_data):
    """Adds basal rate data to dataset columns:
        * basalRate
        * basalDuration
        * basalType
    """

    # Add basal rates
    basal_num = np.random.randint(1, 12)
    basal_rates = np.random.uniform(0.5, 3, basal_num).round(1)
    start_times = np.sort(
            np.random.choice(np.arange(24), basal_num, replace=False)
    )
    basal_map = dict(zip(start_times, basal_rates))

    hourly_rates = pd.Series(np.arange(24)).map(basal_map).ffill()
    hourly_rates.fillna(hourly_rates.values[-1], inplace=True)
    hourly_map = dict(zip(hourly_rates.index, hourly_rates))

    hourly_ts = pd.to_datetime(sample_dataset.timeLocal).dt.hour

    basal_rate_ts = hourly_ts.map(hourly_map)
    sample_dataset['basalRate'] = basal_rate_ts

    # Add Basal Durations
    basal_durations = 60 * np.diff(
            np.concatenate(
                    [start_times, [1 + start_times[-1] + start_times[0]]]
            )
    )

    basal_duration_map = dict(zip(start_times, basal_durations))

    hourly_duration = pd.Series(np.arange(24)).map(basal_duration_map).ffill()
    hourly_duration.fillna(hourly_duration.values[-1], inplace=True)
    hourly_duration_map = dict(zip(hourly_duration.index, hourly_duration))

    basal_duration_ts = hourly_ts.map(hourly_duration_map)

    sample_dataset['basalDuration'] = basal_duration_ts

    sample_dataset['basalType'] = 'scheduled'

    return sample_dataset


def add_alarm_data(sample_dataset, days_of_data):
    """Adds alarm data to dataset to dataset columns:
        * alarmCGMStatus
        * alarmCGMType
        * alarmPumpStatus
        * alarmPumpType
    """

    cgm_alarm_samples = days_of_data//3
    cgm_alarm_indices = np.random.choice(
            sample_dataset.index,
            cgm_alarm_samples,
            replace=False
    )
    sample_dataset.loc[cgm_alarm_indices, 'alarmCGMStatus'] = "vibrate"
    sample_dataset.loc[cgm_alarm_indices, 'alarmCGMType'] = "hyper_alert"

    pump_alarm_samples = days_of_data//3
    pump_alarm_indices = np.random.choice(
            sample_dataset.index,
            pump_alarm_samples,
            replace=False
    )
    sample_dataset.loc[pump_alarm_indices, 'alarmPumpStatus'] = "beep"
    sample_dataset.loc[pump_alarm_indices, 'alarmPumpType'] = "occulsion"

    return sample_dataset


def add_settings_data(sample_dataset):
    """Adds settings data to dataset columns:
        * settingsPumpBGTarget
        * settingsPumpInsulinSensitivity
        * settingsPumpCarbRatio
    """

    settings_num = np.random.randint(1, 12)
    bg_targets = np.random.uniform(70, 160, settings_num).round()
    isfs = np.random.uniform(15, 60, settings_num).round()
    cirs = np.random.uniform(5, 20, settings_num).round()

    start_times = np.sort(
            np.random.choice(np.arange(24), settings_num, replace=False)
    )
    bg_target_map = dict(zip(start_times, bg_targets))
    isf_map = dict(zip(start_times, isfs))
    cir_map = dict(zip(start_times, cirs))

    hourly_targets = pd.Series(np.arange(24)).map(bg_target_map).ffill()
    hourly_targets.fillna(hourly_targets.values[-1], inplace=True)
    hourly_target_map = dict(zip(hourly_targets.index, hourly_targets))

    hourly_isfs = pd.Series(np.arange(24)).map(isf_map).ffill()
    hourly_isfs.fillna(hourly_isfs.values[-1], inplace=True)
    hourly_isf_map = dict(zip(hourly_isfs.index, hourly_isfs))

    hourly_cir = pd.Series(np.arange(24)).map(cir_map).ffill()
    hourly_cir.fillna(hourly_cir.values[-1], inplace=True)
    hourly_cir_map = dict(zip(hourly_cir.index, hourly_cir))

    hourly_ts = pd.to_datetime(sample_dataset.timeLocal).dt.hour

    bg_target_ts = hourly_ts.map(hourly_target_map)
    isf_ts = hourly_ts.map(hourly_isf_map)
    cir_ts = hourly_ts.map(hourly_cir_map)

    sample_dataset['settingsPumpBGTarget'] = bg_target_ts
    sample_dataset['settingsPumpInsulinSensitivity'] = isf_ts
    sample_dataset['settingsPumpCarbRatio'] = cir_ts

    return sample_dataset


def make_dataset(days_of_data):
    """Main function wrapper to create a sample normalized dataset"""

    # Start with empty dataset template
    sample_dataset = create_dataframe_template()

    # Create timeseries with a certain # days of data
    sample_dataset = add_time_data(sample_dataset, days_of_data)

    # Add settings and basal rates
    sample_dataset = add_settings_data(sample_dataset)
    sample_dataset = add_basal_data(sample_dataset, days_of_data)

    # Add in carb entries
    sample_dataset = add_carb_data(sample_dataset, days_of_data)

    # Add insulin data based on carbs and settings
    sample_dataset = add_insulin_data(sample_dataset, days_of_data)

    # Add exercise data
    sample_dataset = add_exercise_data(sample_dataset, days_of_data)

    # Add blood glucose data
    sample_dataset = add_bgValue_data(sample_dataset, days_of_data)

    # Add alarms
    sample_dataset = add_alarm_data(sample_dataset, days_of_data)

    return sample_dataset


# %% Main function call
if __name__ == "__main__":
    days_of_data = 7
    sample_dataset = make_dataset(days_of_data)
    sample_filename = (
            "sample-normalized-dataset-"
            + str(days_of_data)
            + "-days.csv"
    )
    sample_dataset.to_csv(sample_filename, index=False)
