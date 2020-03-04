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

# %% Functions


def create_dataframe_template():
    """Creates a template of columns to be used by the data generator"""

    df_columns = [
        'timeUTC'
        'timeLocal'
        'timeDevice'
        'bgValueCGM'
        'bgValueSMBG'
        'bgValueCalibration'
        'bgValuePumpCalculator'
        'insulinDeliveredTotal'
        'insulinDeliveredBasal'
        'insulinDeliveredBolus'
        'insulinDeliveredExtended'
        'carbIntake'
        'exerciseStatus'
        'exerciseName'
        'exerciseDuration'
        'exerciseDistance'
        'exerciseEnergy'
        'basalRate'
        'basalDuration'
        'basalType'
        'alarmCGMStatus'
        'alarmCGMType'
        'alarmPumpStatus'
        'alarmPumpType'
        'settingsPumpBGTarget'
        'settingsPumpInsulinSensitivity'
        'settingsPumpCarbRatio'
    ]

    template_df = pd.DataFrame(columns=df_columns)

    return template_df


def add_time_data(
        sample_dataset,
        days_of_data
):
    """Adds contiguously rounded time range to dataset columns:
        * timeUTC
        * timeLocal
        * timeDevice
    """

    return sample_dataset


def add_bgValue_data(sample_dataset):
    """Adds bgValue data to dataset columns:
        * bgValueCGM
        * bgValueSMBG
        * bgValueCalibration
        * bgValuePumpCalculator
    """

    return sample_dataset


def add_insulin_data(sample_dataset):
    """Adds insulin data to dataset to dataset columns:
        * insulinDeliveredTotal
        * insulinDeliveredBasal
        * insulinDeliveredBolus
        * insulinDeliveredExtended
    """

    return sample_dataset


def add_carb_data(sample_dataset):
    """Adds carb data to dataset to dataset columns:
        * carbIntake
    """

    return sample_dataset


def add_exercise_data(sample_dataset):
    """Adds exercise data to dataset to dataset columns:
        * exerciseStatus
        * exerciseName
        * exerciseDuration
        * exerciseDistance
        * exerciseEnergy
    """

    return sample_dataset


def add_basal_data(sample_dataset):
    """Adds basal rate data to dataset columns:
        * basalRate
        * basalDuration
        * basalType
    """

    return sample_dataset


def add_alarm_data(sample_dataset):
    """Adds alarm data to dataset to dataset columns:
        * alarmCGMStatus
        * alarmCGMType
        * alarmPumpStatus
        * alarmPumpType
    """

    return sample_dataset


def add_settings_data(sample_dataset):
    """Adds settings data to dataset columns:
        * settingsPumpBGTarget
        * settingsPumpInsulinSensitivity
        * settingsPumpCarbRatio
    """

    return sample_dataset


def make_dataset():
    """Main function wrapper to create a sample normalized dataset"""

    return sample_dataset


# %% Main function call
if __name__ == "__main__":
    sample_dataset = make_dataset()
