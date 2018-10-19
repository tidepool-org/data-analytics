#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=C0301

"""
description: Process rolling statistics for Tidepool blood glucose
             and insulin pump data.
version: 0.0.1
Created: 9/15/2018
author: Jason Meno
dependencies:
    * requires Tidepool user's data with est.localTime
license: BSD-2-Clause

TODO:

-Add to summary statistics:
    "First date",
    "Last date",
    "CGM days",
    "Pump days",
    "CGM & Pump days"

-Add additional CGM statistics:
    "MAGE",
    "MODD",
    "HBGI",
    "LBGI",
    "CONGA",
    "GRADE",
    "logCV",
    "J-Index",
    "LI",
    "MAG",
    "M-Value"

-Add option to process only CGM/Pump data
-Vectorize basal fill function
-Vectorize insulin on board function
-Vectorize round5minutes function
-Verify basal suspends are correctly implemented
"""
# %% REQUIRED LIBRARIES
import pandas as pd
import numpy as np
import datetime as dt
import os
import argparse
import time

# %% USER INPUTS
codeDescription = "Tidepool Rolling Statistics Tool"

parser = argparse.ArgumentParser(description=codeDescription)

parser.add_argument("-d",
                    "--dataPath",
                    dest="dataPath",
                    default="data",
                    help="Path location containing data to be analyzed")

parser.add_argument("-i",
                    "--input",
                    dest="inputFile",
                    default="",
                    help="Input filename of .csv to analyze")

parser.add_argument("-o",
                    "--outputPath",
                    dest="outputPath",
                    default="./output_results/",
                    help="the output location where the results will be stored")

parser.add_argument("-om",
                    "--outputMode",
                    dest="outputMode",
                    default="DS",
                    help="Three output files available: (R)olling, (D)aily, (S)ummary")

parser.add_argument("-s",
                    "--summaryFile",
                    dest="summaryFile",
                    default="default_rolling_summary_output",
                    help="Output summary .csv filename to append summary statistics")

parser.add_argument("-ds",
                    "--day-start",
                    dest="day_start",
                    default="5:55",
                    help="The exact start of the 24-hour day period (24 hour format)")

parser.add_argument("-rw",
                    "--rollingWindow",
                    dest="rollingWindow",
                    nargs='+',
                    default=["24hr", "7day", "14day", "30day", "90day", "1year"],
                    help="An array of rolling window strings. Ex: [\"24hr\",\"30day\"]")

args = parser.parse_args()

# %% Function Definitions

# Classify data by CGM, Pump, or Mixed (CGM+Pump)


def classify_data(dataPath, filename):
    print("Data Classification...", end=" ")
    cgm_bool = False
    class_type = "NA"

    file_loc = os.path.join(dataPath, filename+".csv")

    # Read the first line of file
    with open(file_loc, 'r') as f:
        header = f.readline()

    if "value" in header:
        cgm_bool = True
        class_type = "CGM"
    if "normal" in header:
        if cgm_bool:
            class_type = "MIXED"
        else:
            class_type = "PUMP"

    print("done")
    return class_type

# Read in data by class type
# Returns separate dataframes for cgm/bolus/basal/uploads


def read_data(dataPath, filename, class_type):

    print("Reading Data...", end=" ")
    cgm_data = []
    bolus_data = []
    basal_data = []

    file_loc = os.path.join(dataPath, filename+".csv")

    if class_type == "MIXED":
        # Both CGM & Pump data
        col_names = ['carbInput',
                     'deviceTime',
                     'id',
                     'time',
                     'bolus',
                     'type',
                     'uploadId',
                     'value',
                     'est.type',
                     'est.localTime',
                     'extended',
                     'normal',
                     'rate',
                     'duration'
                     ]

        df = pd.read_csv(file_loc, usecols=col_names, low_memory=False)

        # Removing "UNCERTAIN" est.type (since no est.localTime is evaluated)
        df = df[df["est.type"] != "UNCERTAIN"].copy()

        cgm_data = df[df["type"] == "cbg"].copy()
        bolus_data = df[df["type"] == "bolus"].copy()
        basal_data = df[df["type"] == "basal"].copy()
        upload_data = df[df["type"] == "upload"].copy()

    elif class_type == "PUMP":
        # Pump data only
        col_names = ['carbInput',
                     'deviceTime',
                     'id',
                     'time',
                     'type',
                     'uploadId',
                     'est.type',
                     'est.localTime',
                     'extended',
                     'normal',
                     'rate',
                     'duration'
                     ]

        df = pd.read_csv(file_loc, usecols=col_names, low_memory=False)

        # Removing "UNCERTAIN" est.type (since no est.localTime is evaluated)
        df = df[df["est.type"] != "UNCERTAIN"].copy()

        bolus_data = df[df["type"] == "bolus"].copy()
        basal_data = df[df["type"] == "basal"].copy()
        upload_data = df[df["type"] == "upload"].copy()

    else:
        # CGM data only
        col_names = ['deviceTime',
                     'id',
                     'type',
                     'time',
                     'uploadId',
                     'value',
                     'est.type',
                     'est.localTime',
                     ]

        df = pd.read_csv(file_loc, usecols=col_names, low_memory=False)

        # Removing "UNCERTAIN" est.type (since no est.localTime is evaluated)
        df = df[df["est.type"] != "UNCERTAIN"].copy()

        cgm_data = df[df["type"] == "cbg"].copy()
        upload_data = df[df["type"] == "upload"].copy()

    first_date = df["est.localTime"].min()
    last_date = df["est.localTime"].max()

    print("done")
    return cgm_data, bolus_data, basal_data, upload_data, first_date, last_date


def remove_duplicates(df, upload_data):

    # Sort uploads by oldest uploads first
    upload_data = upload_data.sort_values(ascending=True, by="est.localTime")

    # Create an ordered dictionary (i.e. uploadId1 = 1, ,uploadId2 = 2, etc)
    upload_order_dict = dict(
                            zip(upload_data["uploadId"],
                                list(range(1, 1+len(upload_data.uploadId.unique())))
                                )
                            )

    # Sort data by upload order from the ordered dictionary
    df["upload_order"] = df["uploadId"]
    df["upload_order"] = df["upload_order"].map(upload_order_dict)
    df = df.sort_values(ascending=True, by="upload_order")

    # Replace any healthkit data deviceTimes (NaN) with a unique id
    # This prevents healthkit data with blank deviceTimes from being removed
    df.deviceTime.fillna(df.id, inplace=True)

    # Drop duplicates using est.localTime+value, time(utc time)+value,
    # deviceTime+value, and est.localTime alone
    # The last entry is kept, which contains the most recent upload data
    values_before_removal = len(df.value)
    df = df.drop_duplicates(subset=["est.localTime", "value"], keep="last")
    df = df.drop_duplicates(subset=["time", "value"], keep="last")
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

    # sort ascendingly by est.localTime
    df.sort_values(by="est.localTime", ascending=True, inplace=True)
    df.reset_index(drop=True, inplace=True)

    # calculate the time-in-between (TIB) consecutive records
    t = pd.to_datetime(df["est.localTime"])
    t_shift = pd.to_datetime(df["est.localTime"].shift(1))
    df["TIB"] = round((t - t_shift).dt.days*(86400/300) +
                      (t - t_shift).dt.seconds/300) * 5

    # separate the data into chunks if TIB is greater than 5 minutes
    largeGaps = list(df.query("TIB > 5").index)
    largeGaps.insert(0, 0)
    largeGaps.append(len(df))

    # loop through each chunk to get the cumulative sum and the rounded time
    for gIndex in range(0, len(largeGaps) - 1):

        df.loc[largeGaps[gIndex], "TIB"] = 0

        df.loc[largeGaps[gIndex]:(largeGaps[gIndex + 1] - 1), "TIB_cumsum"] = \
            df.loc[largeGaps[gIndex]:(largeGaps[gIndex + 1] - 1), "TIB"].cumsum()

        df.loc[largeGaps[gIndex]:(largeGaps[gIndex + 1] - 1), "est.localTime_rounded"] = \
            pd.to_datetime(df.loc[largeGaps[gIndex], "est.localTime"]).round("5min") + \
            pd.to_timedelta(df.loc[largeGaps[gIndex]:(largeGaps[gIndex + 1] - 1), "TIB_cumsum"], unit="m")

    # sort descendingly by time
    df.sort_values(by="est.localTime_rounded", ascending=False, inplace=True)
    df.reset_index(drop=True, inplace=True)

    return df

# Fits all data into 5-minute intervals


def fill_time_gaps(df, first_date, last_date, data_type):

    print("Filling in", data_type, "time gaps...", end=" ")
    first_date = pd.to_datetime(dt.datetime.fromtimestamp(pd.to_datetime(first_date).timestamp()+.000001)).round("30S")
    first_date = pd.to_datetime(dt.datetime.fromtimestamp(pd.to_datetime(first_date).timestamp()+.000001)).round("5min")

    last_date = pd.to_datetime(dt.datetime.fromtimestamp(pd.to_datetime(last_date).timestamp()+.000001)).round("30S")
    last_date = pd.to_datetime(dt.datetime.fromtimestamp(pd.to_datetime(last_date).timestamp()+.000001)).round("5min")
    # Create 5-min continuous time series in a new dataframe
    five_min_ts = pd.date_range(first_date, last_date, freq="5min")
    new_df = pd.DataFrame({"est.localTime_rounded": five_min_ts})

    # round est.localTime to nearest 30 seconds, then 5 minutes

    # SLOW BUT MORE ACCURATE
    # df = round5Minutes(df)

    # FAST BUT LESS ACCURATE
    df["est.localTime_rounded"] = pd.to_datetime(pd.to_datetime(df["est.localTime"]).astype(np.int64)+1000).dt.round("30S")
    df["est.localTime_rounded"] = pd.to_datetime(pd.to_datetime(df["est.localTime_rounded"]).astype(np.int64)+1000).dt.round("5min")

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

    rolling_dictionary = dict(zip(
            ["15min", "30min", "1hr", "2hr",
             "3hr", "4hr", "5hr", "6hr",
             "8hr", "12hr", "24hr", "3day",
             "7day", "14day", "30day", "60day",
             "90day", "1year"], list(
                                 [3, 6, 12, 24,
                                  36, 48, 60, 72,
                                  96, 144, 288, 864,
                                  2016, 4032, 8640, 17280,
                                  25920, 105120]
                                            )))

    # Set number of points per rolling window
    rolling_points = np.array(pd.Series(args.rollingWindow).map(rolling_dictionary))
    # Set minimum percentage of points required to calculate rolling statistic
    percent_points = 0.7
    rolling_min = np.floor(percent_points*rolling_points).astype(int)

    print("done")

    print("Starting Rolling Stats")
    rolling_df = pd.DataFrame(index=np.arange(len(df)))
    rolling_df["est.localTime_rounded"] = df["est.localTime_rounded"]
    # Loop through rolling stats for each time prefix
    for i in range(0, len(rolling_prefixes)):

        start_time = time.time()
        rolling_window = df.mg_dL.rolling(rolling_points[i], min_periods=rolling_min[i])

        rolling_df[rolling_prefixes[i]+"_cgm_points"] = rolling_window.count()
        rolling_df[rolling_prefixes[i]+"_cgm_mean"] = rolling_window.mean()
        # get estimated HbA1c or Glucose Management Index (GMI)
        # GMI(%) = 3.31 + 0.02392 x [mean glucose in mg/dL]
        # https://www.jaeb.org/gmi/
        rolling_df[rolling_prefixes[i]+"_cgm_eA1c"] = 3.31 + (0.02392*rolling_df[rolling_prefixes[i]+"_cgm_mean"])
        rolling_df[rolling_prefixes[i]+"_cgm_SD"] = rolling_window.std()
        rolling_df[rolling_prefixes[i]+"_cgm_CV"] = rolling_df[rolling_prefixes[i]+"_cgm_SD"]/rolling_df[rolling_prefixes[i]+"_cgm_mean"]
        rolling_df[rolling_prefixes[i]+"_cgm_percent-below54"] = df["bool_below54"].rolling(rolling_points[i], min_periods=rolling_min[i]).sum()/rolling_df[rolling_prefixes[i]+"_cgm_points"]
        rolling_df[rolling_prefixes[i]+"_cgm_percent-54-70"] = df["bool_54-70"].rolling(rolling_points[i], min_periods=rolling_min[i]).sum()/rolling_df[rolling_prefixes[i]+"_cgm_points"]
        rolling_df[rolling_prefixes[i]+"_cgm_percent-below70"] = df["bool_below70"].rolling(rolling_points[i], min_periods=rolling_min[i]).sum()/rolling_df[rolling_prefixes[i]+"_cgm_points"]
        rolling_df[rolling_prefixes[i]+"_cgm_percent-70-140"] = df["bool_70-140"].rolling(rolling_points[i], min_periods=rolling_min[i]).sum()/rolling_df[rolling_prefixes[i]+"_cgm_points"]
        rolling_df[rolling_prefixes[i]+"_cgm_percent-70-180"] = df["bool_70-180"].rolling(rolling_points[i], min_periods=rolling_min[i]).sum()/rolling_df[rolling_prefixes[i]+"_cgm_points"]
        rolling_df[rolling_prefixes[i]+"_cgm_percent-above180"] = df["bool_above180"].rolling(rolling_points[i], min_periods=rolling_min[i]).sum()/rolling_df[rolling_prefixes[i]+"_cgm_points"]
        rolling_df[rolling_prefixes[i]+"_cgm_percent-above250"] = df["bool_above250"].rolling(rolling_points[i], min_periods=rolling_min[i]).sum()/rolling_df[rolling_prefixes[i]+"_cgm_points"]
        rolling_df[rolling_prefixes[i]+"_cgm_min"] = rolling_window.min()

        # Quartiles take a long time to process.
        # Uncomment if needed

        # rolling_df[rolling_prefixes[i]+"_cgm_10percentile"] = \
        #   rolling_window.quantile(0.1)
        #
        # rolling_df[rolling_prefixes[i]+"_cgm_25percentile"] = \
        #    rolling_window.quantile(0.25)
        # rolling_df[rolling_prefixes[i]+"_cgm_50percentile"] = \
        #    rolling_window.quantile(0.5)
        # rolling_df[rolling_prefixes[i]+"_cgm_75percentile"] = \
        #    rolling_window.quantile(0.75)
        # rolling_df[rolling_prefixes[i]+"_cgm_90percentile"] = \
        #    rolling_window.quantile(0.9)
        # rolling_df[rolling_prefixes[i]+"_cgm_max"] = rolling_window.max()
        # rolling_df[rolling_prefixes[i]+"_IQR"] = \
        #    rolling_df[rolling_prefixes[i]+"_cgm_75percentile"]\
        #    - rolling_df[rolling_prefixes[i]+"_cgm_25percentile"]

        rolling_df[rolling_prefixes[i]+"_events-below54"] = \
            df["event-below54"].rolling(rolling_points[i],
                                        min_periods=rolling_min[i]).sum()
        rolling_df[rolling_prefixes[i]+"_avg-dur-below54"] = df["dur-below54"].rolling(rolling_points[i], min_periods=rolling_min[i]).sum()/rolling_df[rolling_prefixes[i]+"_events-below54"]
        rolling_df[rolling_prefixes[i]+"_events-below70"] = df["event-below70"].rolling(rolling_points[i] ,min_periods=rolling_min[i]).sum()
        rolling_df[rolling_prefixes[i]+"_avg-dur-below70"] = df["dur-below70"].rolling(rolling_points[i], min_periods=rolling_min[i]).sum()/rolling_df[rolling_prefixes[i]+"_events-below70"]
        rolling_df[rolling_prefixes[i]+"_events-above140"] = df["event-above140"].rolling(rolling_points[i], min_periods=rolling_min[i]).sum()
        rolling_df[rolling_prefixes[i]+"_avg-dur-above140"] = df["dur-above140"].rolling(rolling_points[i], min_periods=rolling_min[i]).sum()/rolling_df[rolling_prefixes[i]+"_events-above140"]
        rolling_df[rolling_prefixes[i]+"_events-above180"] = df["event-above180"].rolling(rolling_points[i], min_periods=rolling_min[i]).sum()
        rolling_df[rolling_prefixes[i]+"_avg-dur-above180"] = df["dur-above180"].rolling(rolling_points[i], min_periods=rolling_min[i]).sum()/rolling_df[rolling_prefixes[i]+"_events-above180"]
        rolling_df[rolling_prefixes[i]+"_events-above250"] = df["event-above250"].rolling(rolling_points[i], min_periods=rolling_min[i]).sum()
        rolling_df[rolling_prefixes[i]+"_avg-dur-above250"] = df["dur-above250"].rolling(rolling_points[i], min_periods=rolling_min[i]).sum()/rolling_df[rolling_prefixes[i]+"_events-above250"]

        print(rolling_prefixes[i], ' took {0} seconds.'.format(time.time() - start_time))

    return rolling_df


def get_daily_stats(df, daytime_start):

    daily_df = df.copy()
    daily_df.set_index("est.localTime_rounded", inplace=True)

    # Isolate all statistics to just rows at daytime_start (default 5:55)
    daily_df = daily_df.at_time(daytime_start)

    # Move time back 6 hours so that each row represents the appropriate day
    daily_df.index = daily_df.index-dt.timedelta(hours=6)

    return daily_df


def get_summary_stats(filename, df, day_df):
    summary_df = pd.DataFrame(columns=day_df.columns.tolist())
    summary_df.loc[0] = day_df.iloc[-1]
    summary_df["filename"] = filename
    summary_df.set_index("filename", inplace=True)

    return summary_df

########################################
# %% Main Script - Begin Function Calls#
########################################


full_file_path = os.path.join(os.getcwd(),
                              args.dataPath,
                              args.inputFile+'.csv')

if not os.path.exists(full_file_path):
    print("ERROR: No file found at "+full_file_path)

else:
    donor_class = classify_data(args.dataPath, args.inputFile)

    cgm_df, bolus_df, basal_df, upload_df, first_ts, last_ts = \
        read_data(args.dataPath, args.inputFile, donor_class)

    # Class processing
    if(donor_class == "MIXED"):

        print("Removing Duplicates...", end=" ")
        # Remove Duplicates
        cgm_df, cgm_duplicate_count = \
            remove_duplicates(cgm_df, upload_df)

        bolus_df, bolus_duplicate_count = \
            remove_duplicates(bolus_df, upload_df)

        basal_df, basal_duplicate_count = \
            remove_duplicates(basal_df, upload_df)
        print("done")

        # Fill in time-series gaps
        cgm_df, cgm_rounded_duplicate_count = \
            fill_time_gaps(cgm_df, first_ts, last_ts, "cgm")
        bolus_df, bolus_rounded_duplicate_count = \
            fill_time_gaps(bolus_df, first_ts, last_ts, "bolus")
        basal_df, basal_rounded_duplicate_count = \
            fill_time_gaps(basal_df, first_ts, last_ts, "basal")

        final_df = cgm_df.copy()
        final_df["basal_rate"] = basal_df["rate"].copy()
        final_df["bolus_normal"] = bolus_df["normal"].copy()
        final_df["bolus_extended"] = bolus_df["extended"].copy()

    elif(donor_class == "PUMP"):
        print("Removing Duplicates...", end=" ")
        # Remove Duplicates

        bolus_df, bolus_duplicate_count = \
            remove_duplicates(bolus_df, upload_df)
        basal_df, basal_duplicate_count = \
            remove_duplicates(basal_df, upload_df)
        print("done")
        print("Removing Rounded Duplicates...", end=" ")
        # Fill in time-series gaps

        bolus_df, bolus_rounded_duplicate_count = \
            fill_time_gaps(bolus_df, first_ts, last_ts, "bolus")
        basal_df, basal_rounded_duplicate_count = \
            fill_time_gaps(basal_df, first_ts, last_ts, "basal")
        print("done")

        final_df = bolus_df.copy()
        final_df["value"] = np.NaN
        final_df["basal_rate"] = basal_df["rate"].copy()
        final_df["bolus_normal"] = bolus_df["normal"].copy()
        final_df["bolus_extended"] = bolus_df["extended"].copy()

    else:
        print("Removing Duplicates...", end=" ")
        # Remove Duplicates
        cgm_df, cgm_duplicate_count = \
            remove_duplicates(cgm_df, upload_df)

        print("done")
        print("Removing Rounded Duplicates...", end=" ")
        # Fill in time-series gaps
        cgm_df, cgm_rounded_duplicate_count = \
            fill_time_gaps(cgm_df, first_ts, last_ts, "cgm")

        print("done")

        final_df = cgm_df.copy()
        final_df["basal_rate"] = np.NaN
        final_df["bolus_normal"] = np.NaN
        final_df["bolus_extended"] = np.NaN

    # %% Start statistics gathering and output
    rolling_df = get_rolling_stats(final_df, args.rollingWindow)

    if not os.path.exists(args.outputPath):
        os.mkdir(args.outputPath)

    print("Saving files")

    # Three output files available: (R)olling, (D)aily, (S)ummary

    # Rolling output saves entire dataframe at 5 minutes resolution
    if "R" in args.outputMode:
        rolling_df.to_csv(os.path.join(args.outputPath,
                                       args.inputFile +
                                       '_rolling_output.csv'))

    # Daily output saves dataframe with day-level statistics
    if "D" in args.outputMode:
        daily_df = get_daily_stats(rolling_df, args.day_start)
        daily_df.to_csv(os.path.join(args.outputPath,
                                     args.inputFile +
                                     '_daily_output.csv'))

    # Summary output appends the last line of the rolling statistics to a file
    if "S" in args.outputMode:

        summary_df = get_summary_stats(args.inputFile, final_df, daily_df)
        summary_path = os.path.join(args.outputPath,
                                    args.summaryFile +
                                    '.csv')

        if not os.path.exists(summary_path):
            summary_df.to_csv(summary_path, header=True)
        else:
            summary_df.to_csv(summary_path, mode='a', header=False)

    else:
        print("WARNING: Summary file not specified." +
              " Defaulting to \"default_rolling_summary_output.csv\"")

    print("done")
