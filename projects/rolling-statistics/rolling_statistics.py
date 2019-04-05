#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=C0301

"""
description: Pipeline for processing Tidepool CGM rolling statistics
version: 0.0.2
Created: 3/01/2019
author: Jason Meno
dependencies:
    * Tidepool account with CGM data
license: BSD-2-Clause

TODO:

    * Add mmol/l metrics
    * Add support for Freestyle Libre data
    * Add rolling stats for insulin pump data (basal/bolus)

"""
# %% Import

import os
from os.path import join, dirname, isfile
import pandas as pd
import datetime as dt
import numpy as np
import argparse
import sys
from plotly import tools
from plotly.offline import download_plotlyjs, init_notebook_mode,  iplot, plot

sys.path.insert(0, "dependencies")
from data_processing_functions import *  # noqa: E402

# %% Argument Input Parsing
codeDescription = "Tidepool Rolling Statistics Tool"

parser = argparse.ArgumentParser(description=codeDescription)

parser.add_argument("-i",
                    "--input",
                    dest="input_file",
                    default="",
                    help="Optional specified input file.")

parser.add_argument("-years",
                    "--years_of_data",
                    dest="years_of_data",
                    default=10,
                    help="Number of years of data to retrieve from API")

parser.add_argument("-rw",
                    "--rolling_windows",
                    dest="rolling_windows",
                    nargs='+',
                    default=["1day", "3day", "7day", "14day", "21day", "30day", "60day", "90day", "180day", "365day"],
                    help="An array of rolling window strings. Ex: 1day 7day 30day 365day OR continuous")

parser.add_argument("-viz",
                    "--visualize",
                    dest="visualize",
                    default=True,
                    help="True/False whether to output plotly visualization of data")

args = parser.parse_args()

# If continous argument passed for rolling windows
# Apply an increasing rolling window from 1 day to 30 days
if('continuous' in args.rolling_windows):
    args.rolling_windows = list(pd.Series(np.arange(1, 31, 1)).apply(lambda x: str(x) + 'day'))


# %% Rolling Stats Functions
def get_rolling_stats(df, rolling_prefixes):

    # Run Length Encoding 
    # This is used to calculate daily hypo/hyper events and duration
    # Credit to Thomas Browne for the vectorized python format
    
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
            i = np.append(np.where(y), n - 1)    # must include last element position
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

    # Calculate LBGI and HBGI using equation from
    # Clarke, W., & Kovatchev, B. (2009)

    transformed_bg = 1.509*((np.log(df["mg_dL"])**1.084)-5.381)
    risk_power = 10*(transformed_bg)**2
    low_risk_bool = transformed_bg < 0
    high_risk_bool = transformed_bg > 0
    df["low_risk_power"] = risk_power * low_risk_bool
    df["high_risk_power"] = risk_power * high_risk_bool

    # Setup sleep data (12AM-6AM)
    sleep_bool = np.array((df["est.localTime_rounded"].dt.hour*60+df["est.localTime_rounded"].dt.minute) < 360)
    df["sleep_values"] = df.loc[sleep_bool, "mg_dL"]

    # Setup run length encoding for sleep events
    rle_sleep_below54 = rle(df.sleep_values < 54)
    rle_sleep_below70 = rle(df.sleep_values < 70)
    rle_sleep_above140 = rle(df.sleep_values > 140)
    rle_sleep_above180 = rle(df.sleep_values > 180)
    rle_sleep_above250 = rle(df.sleep_values > 250)

    sleep_col_names = ["sleep_event-below54",
                       "sleep_dur-below54",
                       "sleep_event-below70",
                       "sleep_dur-below70",
                       "sleep_event-above140",
                       "sleep_dur-above140",
                       "sleep_event-above180",
                       "sleep_dur-above180",
                       "sleep_event-above250",
                       "sleep_dur-above250"]

    df.reindex(columns=[df.columns.tolist()+sleep_col_names])

    df["sleep_below54"] = df.sleep_values < 54
    df["sleep_54-70"] = (df.sleep_values >= 54) & (df.sleep_values <= 70)
    df["sleep_below70"] = df.sleep_values < 70
    df["sleep_70-140"] = (df.sleep_values >= 70) & (df.sleep_values <= 140)
    df["sleep_70-180"] = (df.sleep_values >= 70) & (df.sleep_values <= 180)
    df["sleep_above180"] = df.sleep_values > 180
    df["sleep_above250"] = df.sleep_values > 250


    below54_sleep_loc = rle_sleep_below54[1][np.where((rle_sleep_below54[2] == True) & (rle_sleep_below54[0] >= 3))]
    below54_sleep_dur = 5*rle_sleep_below54[0][np.where((rle_sleep_below54[2] == True) & (rle_sleep_below54[0] >= 3))]
    df["sleep_event-below54"] = False
    df.loc[below54_sleep_loc, "sleep_event-below54"] = True
    df["sleep_dur-below54"] = 0
    df.loc[below54_sleep_loc, "sleep_dur-below54"] = below54_sleep_dur

    below70_sleep_loc = rle_sleep_below70[1][np.where((rle_sleep_below70[2] == True) & (rle_sleep_below70[0] >= 3))]
    below70_sleep_dur = 5*rle_sleep_below70[0][np.where((rle_sleep_below70[2] == True) & (rle_sleep_below70[0] >= 3))]
    df["sleep_event-below70"] = False
    df.loc[below70_sleep_loc, "sleep_event-below70"] = True
    df["sleep_dur-below70"] = 0
    df.loc[below70_sleep_loc, "sleep_dur-below70"] = below70_sleep_dur

    above140_sleep_loc = rle_sleep_above140[1][np.where((rle_sleep_above140[2] == True) & (rle_sleep_above140[0] >= 3))]
    above140_sleep_dur = 5*rle_sleep_above140[0][np.where((rle_sleep_above140[2] == True) & (rle_sleep_above140[0] >= 3))]
    df["sleep_event-above140"] = False
    df.loc[above140_sleep_loc, "sleep_event-above140"] = True
    df["sleep_dur-above140"] = 0
    df.loc[above140_sleep_loc, "sleep_dur-above140"] = above140_sleep_dur

    above180_sleep_loc = rle_sleep_above180[1][np.where((rle_sleep_above180[2] == True) & (rle_sleep_above180[0] >= 3))]
    above180_sleep_dur = 5*rle_sleep_above180[0][np.where((rle_sleep_above180[2] == True) & (rle_sleep_above180[0] >= 3))]
    df["sleep_event-above180"] = False
    df.loc[above180_sleep_loc, "sleep_event-above180"] = True
    df["sleep_dur-above180"] = 0
    df.loc[above180_sleep_loc, "sleep_dur-above180"] = above180_sleep_dur

    above250_sleep_loc = rle_sleep_above250[1][np.where((rle_sleep_above250[2] == True) & (rle_sleep_above250[0] >= 3))]
    above250_sleep_dur = 5*rle_sleep_above250[0][np.where((rle_sleep_above250[2] == True) & (rle_sleep_above250[0] >= 3))]
    df["sleep_event-above250"] = False
    df.loc[above250_sleep_loc, "sleep_event-above250"] = True
    df["sleep_dur-above250"] = 0
    df.loc[above250_sleep_loc, "sleep_dur-above250"] = above250_sleep_dur

    df["sleep_low_risk_power"] = df.loc[sleep_bool, "low_risk_power"]
    df["sleep_high_risk_power"] = df.loc[sleep_bool, "high_risk_power"]
    
    # Set up rolling windows
    day_string_list = list(pd.Series(np.arange(1,366,1)).apply(lambda x: str(x)+'day'))
    day_points_list = np.arange(1, 366, 1)*288
    
    rolling_dictionary = dict(zip(day_string_list, day_points_list))

    # Set number of points per rolling window
    rolling_points = np.array(pd.Series(rolling_prefixes).map(rolling_dictionary))
    
    # Set minimum percentage of points required to calculate rolling statistic
    percent_points = 0.7
    rolling_min = np.ceil(percent_points*rolling_points).astype(int)

    rolling_df = pd.DataFrame(index=np.arange(len(df)))
    rolling_df["est.localTime_rounded"] = df["est.localTime_rounded"]
    
    print('Calculating Rolling Stats... ', end="")
    # Loop through rolling stats for each time prefix
    for prefix_loc in range(0, len(rolling_prefixes)):
        print(rolling_prefixes[prefix_loc], " ", end="")
        
        rolling_window = df.mg_dL.rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc])

        rolling_df[rolling_prefixes[prefix_loc]+"_n-data-points"] = rolling_window.count()
        rolling_df[rolling_prefixes[prefix_loc]+"_percent-data-available"] = rolling_df[rolling_prefixes[prefix_loc]+"_n-data-points"]/rolling_points[prefix_loc]
        rolling_df[rolling_prefixes[prefix_loc]+"_mean"] = rolling_window.mean()
        # get estimated HbA1c or Glucose Management Index (GMI)
        # GMI(%) = 3.31 + 0.02392 x [mean glucose in mg/dL]
        # https://www.jaeb.org/gmi/
        rolling_df[rolling_prefixes[prefix_loc]+"_GMI"] = 3.31 + (0.02392*rolling_df[rolling_prefixes[prefix_loc]+"_mean"])
        rolling_df[rolling_prefixes[prefix_loc]+"_SD"] = rolling_window.std()
        rolling_df[rolling_prefixes[prefix_loc]+"_CV"] = rolling_df[rolling_prefixes[prefix_loc]+"_SD"]/rolling_df[rolling_prefixes[prefix_loc]+"_mean"]
        rolling_df[rolling_prefixes[prefix_loc]+"_percent-below54"] = df["bool_below54"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_n-data-points"]
        rolling_df[rolling_prefixes[prefix_loc]+"_percent-54-70"] = df["bool_54-70"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_n-data-points"]
        rolling_df[rolling_prefixes[prefix_loc]+"_percent-below70"] = df["bool_below70"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_n-data-points"]
        rolling_df[rolling_prefixes[prefix_loc]+"_percent-70-140"] = df["bool_70-140"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_n-data-points"]
        rolling_df[rolling_prefixes[prefix_loc]+"_percent-70-180"] = df["bool_70-180"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_n-data-points"]
        rolling_df[rolling_prefixes[prefix_loc]+"_percent-above180"] = df["bool_above180"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_n-data-points"]
        rolling_df[rolling_prefixes[prefix_loc]+"_percent-above250"] = df["bool_above250"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_n-data-points"]
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

        # Rolling stats for events (in a range for >=15min)
        # If there are 0 events, division is null
        # Solution: Replace nulls with the 0 event column value
        rolling_df[rolling_prefixes[prefix_loc]+"_events-below54"] = df["event-below54"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()
        rolling_df[rolling_prefixes[prefix_loc]+"_avg-time-below54"] = df["dur-below54"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_events-below54"]
        rolling_df[rolling_prefixes[prefix_loc]+"_avg-time-below54"].fillna(value=rolling_df[rolling_prefixes[prefix_loc]+"_events-below54"], inplace=True)

        rolling_df[rolling_prefixes[prefix_loc]+"_events-below70"] = df["event-below70"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()
        rolling_df[rolling_prefixes[prefix_loc]+"_avg-time-below70"] = df["dur-below70"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_events-below70"]
        rolling_df[rolling_prefixes[prefix_loc]+"_avg-time-below70"].fillna(value=rolling_df[rolling_prefixes[prefix_loc]+"_events-below70"], inplace=True)

        rolling_df[rolling_prefixes[prefix_loc]+"_events-above140"] = df["event-above140"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()
        rolling_df[rolling_prefixes[prefix_loc]+"_avg-time-above140"] = df["dur-above140"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_events-above140"]
        rolling_df[rolling_prefixes[prefix_loc]+"_avg-time-above140"].fillna(value=rolling_df[rolling_prefixes[prefix_loc]+"_events-above140"], inplace=True)

        rolling_df[rolling_prefixes[prefix_loc]+"_events-above180"] = df["event-above180"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()
        rolling_df[rolling_prefixes[prefix_loc]+"_avg-time-above180"] = df["dur-above180"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_events-above180"]
        rolling_df[rolling_prefixes[prefix_loc]+"_avg-time-above180"].fillna(value=rolling_df[rolling_prefixes[prefix_loc]+"_events-above180"], inplace=True)

        rolling_df[rolling_prefixes[prefix_loc]+"_events-above250"] = df["event-above250"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()
        rolling_df[rolling_prefixes[prefix_loc]+"_avg-time-above250"] = df["dur-above250"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_events-above250"]
        rolling_df[rolling_prefixes[prefix_loc]+"_avg-time-above250"].fillna(value=rolling_df[rolling_prefixes[prefix_loc]+"_events-above250"], inplace=True)

        rolling_df[rolling_prefixes[prefix_loc]+"_AUC-avg_below54"] = df["below54_vals"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).apply(lambda x: np.trapz(x, dx=5), raw=True)/(rolling_points[prefix_loc]/288)
        rolling_df[rolling_prefixes[prefix_loc]+"_AUC-avg_below70"] = df["below70_vals"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).apply(lambda x: np.trapz(x, dx=5), raw=True)/(rolling_points[prefix_loc]/288)
        rolling_df[rolling_prefixes[prefix_loc]+"_AUC-avg_70-140"] = df["70-140_vals"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).apply(lambda x: np.trapz(x, dx=5), raw=True)/(rolling_points[prefix_loc]/288)
        rolling_df[rolling_prefixes[prefix_loc]+"_AUC-avg_70-180"] = df["70-180_vals"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).apply(lambda x: np.trapz(x, dx=5), raw=True)/(rolling_points[prefix_loc]/288)
        rolling_df[rolling_prefixes[prefix_loc]+"_AUC-avg_above180"] = df["above180_vals"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).apply(lambda x: np.trapz(x, dx=5), raw=True)/(rolling_points[prefix_loc]/288)
        rolling_df[rolling_prefixes[prefix_loc]+"_AUC-avg_above250"] = df["above250_vals"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).apply(lambda x: np.trapz(x, dx=5), raw=True)/(rolling_points[prefix_loc]/288)

        rolling_df[rolling_prefixes[prefix_loc]+"_LBGI"] = df["low_risk_power"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).mean()
        rolling_df[rolling_prefixes[prefix_loc]+"_HBGI"] = df["high_risk_power"].rolling(rolling_points[prefix_loc], min_periods=rolling_min[prefix_loc]).mean()
    
        # Sleep specific rolling stats
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep-n-data-points"] = df["sleep_values"].rolling(rolling_points[prefix_loc], min_periods=1).count()
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep-percent-data-available"] = rolling_df[rolling_prefixes[prefix_loc]+"_sleep-n-data-points"]/(72*rolling_points[prefix_loc]/288)
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep-mean"] = df["sleep_values"].rolling(rolling_points[prefix_loc], min_periods=1).mean()
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep-SD"] = df["sleep_values"].rolling(rolling_points[prefix_loc], min_periods=1).std()
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep-CV"] = rolling_df[rolling_prefixes[prefix_loc]+"_sleep-SD"]/rolling_df[rolling_prefixes[prefix_loc]+"_sleep-mean"]

        rolling_df[rolling_prefixes[prefix_loc]+"_sleep-percent-below54"] = df["sleep_below54"].rolling(rolling_points[prefix_loc], min_periods=1).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_sleep-n-data-points"]
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep-percent-54-70"] = df["sleep_54-70"].rolling(rolling_points[prefix_loc], min_periods=1).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_sleep-n-data-points"]
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep-percent-below70"] = df["sleep_below70"].rolling(rolling_points[prefix_loc], min_periods=1).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_sleep-n-data-points"]
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep-percent-70-140"] = df["sleep_70-140"].rolling(rolling_points[prefix_loc], min_periods=1).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_sleep-n-data-points"]
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep-percent-70-180"] = df["sleep_70-180"].rolling(rolling_points[prefix_loc], min_periods=1).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_sleep-n-data-points"]
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep-percent-above180"] = df["sleep_above180"].rolling(rolling_points[prefix_loc], min_periods=1).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_sleep-n-data-points"]
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep-percent-above250"] = df["sleep_above250"].rolling(rolling_points[prefix_loc], min_periods=1).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_sleep-n-data-points"]

        rolling_df[rolling_prefixes[prefix_loc]+"_sleep-events-below54"] = df["sleep_event-below54"].rolling(rolling_points[prefix_loc], min_periods=1).sum()
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep-avg-time-below54"] = df["sleep_dur-below54"].rolling(rolling_points[prefix_loc], min_periods=1).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_sleep-events-below54"]
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep-avg-time-below54"].fillna(value=rolling_df[rolling_prefixes[prefix_loc]+"_sleep-events-below54"], inplace=True)

        rolling_df[rolling_prefixes[prefix_loc]+"_sleep-events-below70"] = df["sleep_event-below70"].rolling(rolling_points[prefix_loc], min_periods=1).sum()
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep-avg-time-below70"] = df["sleep_dur-below70"].rolling(rolling_points[prefix_loc], min_periods=1).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_sleep-events-below70"]
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep-avg-time-below70"].fillna(value=rolling_df[rolling_prefixes[prefix_loc]+"_sleep-events-below70"], inplace=True)

        rolling_df[rolling_prefixes[prefix_loc]+"_sleep-events-above140"] = df["sleep_event-above140"].rolling(rolling_points[prefix_loc], min_periods=1).sum()
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep-avg-time-above140"] = df["sleep_dur-above140"].rolling(rolling_points[prefix_loc], min_periods=1).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_sleep-events-above140"]
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep-avg-time-above140"].fillna(value=rolling_df[rolling_prefixes[prefix_loc]+"_sleep-events-above140"], inplace=True)

        rolling_df[rolling_prefixes[prefix_loc]+"_sleep-events-above180"] = df["sleep_event-above180"].rolling(rolling_points[prefix_loc], min_periods=1).sum()
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep-avg-time-above180"] = df["sleep_dur-above180"].rolling(rolling_points[prefix_loc], min_periods=1).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_sleep-events-above180"]
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep-avg-time-above180"].fillna(value=rolling_df[rolling_prefixes[prefix_loc]+"_sleep-events-above180"], inplace=True)

        rolling_df[rolling_prefixes[prefix_loc]+"_sleep-events-above250"] = df["sleep_event-above250"].rolling(rolling_points[prefix_loc], min_periods=1).sum()
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep-avg-time-above250"] = df["sleep_dur-above250"].rolling(rolling_points[prefix_loc], min_periods=1).sum()/rolling_df[rolling_prefixes[prefix_loc]+"_sleep-events-above250"]
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep-avg-time-above250"].fillna(value=rolling_df[rolling_prefixes[prefix_loc]+"_sleep-events-above250"], inplace=True)

        rolling_df[rolling_prefixes[prefix_loc]+"_sleep-LBGI"] = df["sleep_low_risk_power"].rolling(rolling_points[prefix_loc], min_periods=1).mean()
        rolling_df[rolling_prefixes[prefix_loc]+"_sleep-HBGI"] = df["sleep_high_risk_power"].rolling(rolling_points[prefix_loc], min_periods=1).mean()

        # Replace all metrics with less than required data percentage with NaNs

        metric_list = ["_mean",
                       "_GMI",
                       "_SD",
                       "_CV",
                       "_percent-below54",
                       "_percent-54-70",
                       "_percent-below70",
                       "_percent-70-140",
                       "_percent-70-180",
                       "_percent-above180",
                       "_percent-above250",
                       "_min",
                       "_10percentile",
                       "_25percentile",
                       "_50percentile",
                       "_75percentile",
                       "_90percentile",
                       "_max",
                       "_IQR",
                       "_events-below54",
                       "_avg-time-below54",
                       "_events-below70",
                       "_avg-time-below70",
                       "_events-above140",
                       "_avg-time-above140",
                       "_events-above180",
                       "_avg-time-above180",
                       "_events-above250",
                       "_avg-time-above250",
                       "_AUC-avg_below54",
                       "_AUC-avg_below70",
                       "_AUC-avg_70-140",
                       "_AUC-avg_70-180",
                       "_AUC-avg_above180",
                       "_AUC-avg_above250",
                       "_LBGI",
                       "_HBGI"]

        sleep_metric_list = ["_sleep-mean",
                             "_sleep-SD",
                             "_sleep-CV",
                             "_sleep-percent-below54",
                             "_sleep-percent-54-70",
                             "_sleep-percent-below70",
                             "_sleep-percent-70-140",
                             "_sleep-percent-70-180",
                             "_sleep-percent-above180",
                             "_sleep-percent-above250",
                             "_sleep-events-below54",
                             "_sleep-avg-time-below54",
                             "_sleep-events-below70",
                             "_sleep-avg-time-below70",
                             "_sleep-events-above140",
                             "_sleep-avg-time-above140",
                             "_sleep-events-above180",
                             "_sleep-avg-time-above180",
                             "_sleep-events-above250",
                             "_sleep-avg-time-above250",
                             "_sleep-LBGI",
                             "_sleep-HBGI"]

        metric_names = [rolling_prefixes[prefix_loc]+'{0}'.format(metric) for metric in metric_list]
        sleep_metric_names = [rolling_prefixes[prefix_loc]+'{0}'.format(metric) for metric in sleep_metric_list]

        rolling_df.loc[(rolling_df[rolling_prefixes[prefix_loc]+"_percent-data-available"] < percent_points), metric_names] = np.nan
        rolling_df.loc[(rolling_df[rolling_prefixes[prefix_loc]+"_sleep-percent-data-available"] < percent_points), sleep_metric_names] = np.nan

    print("")
    return rolling_df


def get_daily_stats(df):

    daily_df = df.copy()
    daily_df.set_index("est.localTime_rounded", inplace=True)

    # Isolate all statistics to just rows at 5:55am (end of day)
    daily_df = daily_df.at_time("5:55")

    # Move time back 6 hours so that each row represents the appropriate day
    # Ex: 2019-01-02 5:55 contains rolling stats data for 2019-01-01
    daily_df.index = daily_df.index-dt.timedelta(hours=6)
    daily_df.index = daily_df.index.strftime('%Y-%m-%d')
    daily_df.insert(0, "day", daily_df.index)
    daily_df.reset_index(drop=True, inplace=True)

    return daily_df


# %% Visualize Daily Rolling Stats w/ Plotly Slider
def visualize_data(daily_df, viz_metrics, output_filename):
    graph_rows = len(viz_metrics)
    fig = tools.make_subplots(rows=graph_rows, cols=1, specs=[[{}]]*graph_rows,
                              shared_xaxes=True, shared_yaxes=False,
                              vertical_spacing=0.01)

    trace_row = 1
    for metric_name in viz_metrics:
        ymin = 1000
        ymax = 0

        for window_size in args.rolling_windows:

            metric = window_size+metric_name

            trace = {"x": daily_df["day"],
                     "y": daily_df[metric],
                     "mode": "lines",
                     "name": metric,
                     "type": "scattergl",
                     'visible': False}

            fig.append_trace(trace, trace_row, 1)

            min_val = daily_df[metric].min()
            max_val = daily_df[metric].max()

            if(min_val < ymin):
                ymin = min_val
            if(max_val > ymax):
                ymax = max_val

        if(trace_row < 1):
            fig['layout']['yaxis'].update(title=metric_name.split('_')[1], range=[ymin, ymax])
        else:
            fig['layout']['yaxis'+str(trace_row)].update(title=metric_name.split('_')[1], range=[ymin, ymax])

        trace_row = trace_row + 1

    # Toggle first metrics to visible
    for first_metric_point in range(len(viz_metrics)):
        first_metric_point = first_metric_point*len(args.rolling_windows)
        fig.data[first_metric_point]['visible'] = True

    # Setup slider steps
    steps = []
    for loc in range(len(args.rolling_windows)):
        step = dict(
            method='restyle',
            args=['visible', [False] * len(fig.data)],
            label=args.rolling_windows[loc]
        )

        # Toggle trace visibility for each slider step
        for dist_between_metrics in range(len(viz_metrics)):
            dist_between_metrics = dist_between_metrics*len(args.rolling_windows)
            step['args'][1][loc+dist_between_metrics] = True

        steps.append(step)

    sliders = [dict(
        active=0,
        currentvalue={"prefix": "Rolling Window Size: "},
        pad={"t": 50},
        steps=steps
    )]

    fig["layout"]["sliders"] = sliders

    plot(fig, filename=output_filename)


# %% Main Script

if(args.input_file == ""):
    # Download data from Tidepool API
    data, responses, user_id = get_data_from_api(years_of_data=args.years_of_data)

    if("time" not in list(data)):
        print(user_id + " NO DATA IN ACCOUNT\n")
        exit()

else:
    if(args.input_file.split('.')[-1] == 'csv'):
        data = pd.read_csv(args.input_file, low_memory=False)
    if(args.input_file.split('.')[-1] == 'xlsx'):
        data = pd.read_excel(args.input_file)
    if(args.input_file.split('.')[-1] == 'json'):
        data = pd.read_json(args.input_file)

    user_id = ''

# Estimate Local Time
print("Estimating Local Times")
data = getLTE(data)

if("deviceTime" in list(data)):
    # Fill localTime with deviceTime if getLTE cannot impute (NaT)
    # and deviceTime comes from Dexcom API
    data["est.localTime"].fillna(pd.to_datetime(data.loc[data["isDexcomAPI"], "deviceTime"]), inplace=True)

# Clean Data
print("Cleaning Data")
data = cleanData(data)

# Extract cgm and upload dataframes
cgm_df = data.loc[data.type == "cbg"].copy()
cgm_df["mg_dL"] = (cgm_df.value*18.01559).astype(int)

upload_df = data.loc[data.type == "upload"]

if(len(cgm_df) == 0):
    print(user_id + " NO CGM data available.\n")
    exit()

print("Removing Duplicates... ", end="")
cgm_df, cgm_duplicate_count = remove_duplicates(cgm_df, upload_df)
print(cgm_duplicate_count, "duplicates removed")

startDate = cgm_df["est.localTime"].min()
endDate = cgm_df["est.localTime"].max()

# Rounds data into a 5-minute dataframe
print("Rounded Timestamps... ", end="")
cgm_df, cgm_rounded_duplicate_count = create_rounded_time_range(cgm_df, startDate, endDate, "cgm")
print(cgm_rounded_duplicate_count, "rounded duplicates removed")

clean_cgm_df = cgm_df.copy()

results_outpath = "results"
if not os.path.exists(results_outpath):
    os.mkdir(results_outpath)

output_filepath = os.path.join(results_outpath, "daily_rolling_stats_" + user_id +".csv")

# Import Daily Rolling Stats Data (if it exists)
if(os.path.isfile(output_filepath)):
    print("Importing Daily Rolling Stats Data From ", output_filepath)
    daily_df = pd.read_csv(output_filepath, low_memory=False)

else:
    clean_cgm_df["est.localTime"] = pd.to_datetime(clean_cgm_df["est.localTime"])
    clean_cgm_df["est.localTime_rounded"] = pd.to_datetime(clean_cgm_df["est.localTime_rounded"])

    rolling_df = get_rolling_stats(clean_cgm_df.copy(), args.rolling_windows)
    daily_df = get_daily_stats(rolling_df)
    daily_df.to_csv(output_filepath)

print("FINISHED!")

# %% List of all metrics that can be visualized

metric_list = ["_mean",
               "_GMI",
               "_SD",
               "_CV",
               "_percent-below54",
               "_percent-54-70",
               "_percent-below70",
               "_percent-70-140",
               "_percent-70-180",
               "_percent-above180",
               "_percent-above250",
               "_min",
               "_10percentile",
               "_25percentile",
               "_50percentile",
               "_75percentile",
               "_90percentile",
               "_max",
               "_IQR",
               "_events-below54",
               "_avg-time-below54",
               "_events-below70",
               "_avg-time-below70",
               "_events-above140",
               "_avg-time-above140",
               "_events-above180",
               "_avg-time-above180",
               "_events-above250",
               "_avg-time-above250",
               "_AUC-avg_below54",
               "_AUC-avg_below70",
               "_AUC-avg_70-140",
               "_AUC-avg_70-180",
               "_AUC-avg_above180",
               "_AUC-avg_above250",
               "_LBGI",
               "_HBGI",
               "_sleep-mean",
               "_sleep-SD",
               "_sleep-CV",
               "_sleep-percent-below54",
               "_sleep-percent-54-70",
               "_sleep-percent-below70",
               "_sleep-percent-70-140",
               "_sleep-percent-70-180",
               "_sleep-percent-above180",
               "_sleep-percent-above250",
               "_sleep-events-below54",
               "_sleep-avg-time-below54",
               "_sleep-events-below70",
               "_sleep-avg-time-below70",
               "_sleep-events-above140",
               "_sleep-avg-time-above140",
               "_sleep-events-above180",
               "_sleep-avg-time-above180",
               "_sleep-events-above250",
               "_sleep-avg-time-above250",
               "_sleep-LBGI",
               "_sleep-HBGI"]


# %% Run Plotly Visualization

if(args.visualize):
    viz_metrics = ["mean", "SD"]
    viz_metrics = ['_{0}'.format(metric) for metric in viz_metrics]

    output_filename = 'results/rollng-stats-daily-viz.html'
    visualize_data(daily_df.copy(), viz_metrics, output_filename)
