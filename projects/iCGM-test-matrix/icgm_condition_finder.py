#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iCGM Condition Finder
=====================
:File: icgm_condition_finder.py
:Description: For 9 unique iCGM conditions, the counts and distributions of
              each condition is found in a dataset. One sample timestamp from
              each condition is marked as an evaluation point for analysis.
:Version: 0.0.1
:Created: 2020-01-29
:Authors: Jason Meno (jam)
:Dependencies: A .csv containing Tidepool CGM device data
:License: BSD-2-Clause
"""

# %% Library Imports
import pandas as pd
import numpy as np
import os

# %% Functions


def import_data(file_path):
    """Imports a dataset"""

    data = pd.read_csv(file_path, low_memory=False)

    return data


def create_5min_contiguous_df(cgm_df):
    """
    Fit the CGM trace to a contiguous 5-minute time series to uncover gaps
    """

    cgm_df["rounded_time"] = pd.to_datetime(cgm_df.time).dt.ceil(freq="5min")
    first_timestamp = cgm_df["rounded_time"].min()
    last_timestamp = cgm_df["rounded_time"].max()

    contiguous_ts = pd.date_range(first_timestamp, last_timestamp, freq="5min")
    contiguous_df = pd.DataFrame(contiguous_ts, columns=["rounded_time"])

    contiguous_df = pd.merge(contiguous_df,
                             cgm_df,
                             how="left",
                             on="rounded_time"
                             )

    return contiguous_df


def rolling_30min_median(contiguous_df):
    """
    Calculate the median mg/dL value with a 30-minute (6 points) rolling window
    """

    contiguous_df["rolling_30min_median"] = \
        contiguous_df["value"].rolling(window=6, min_periods=6).median()

    return contiguous_df


def get_slope(y):
    """
    Returns the least squares regression slope given a contiguous sequence y
    """

    # From SciPy lstsq usage Example Guide:
    # Rewrite y = mx + c equation as y = Ap
    # Where A = [[x 1]] and p = [[m], [c]]
    x = np.arange(len(y))
    A = np.vstack([x, np.ones(len(x))]).T
    m, c = np.linalg.lstsq(A, y, rcond=None)[0]

    return m/5  # Divide by the 5-min interval to get mg/dL/min resolution


def rolling_15min_slope(contiguous_df):
    """
    Calculate the slope in mg/dL/min with a 15-minute (3 points) rolling window
    """

    contiguous_df["rolling_15min_slope"] = \
        contiguous_df["value"].rolling(window=3, min_periods=3).apply(
                lambda x: get_slope(x), raw=True)

    return contiguous_df


def rle(inarray):
    """ run length encoding. Partial credit to R rle function.
        Multi datatype arrays catered for including non Numpy
        returns: tuple (runlengths, startpositions, values)

    This function is useful for finding the size of gaps in the data

    Returns 3 arrays:
        - The lengths of each run
        - The location of the start of each run
        - The values contained in each run
    """
    ia = np.asarray(inarray)                  # force numpy
    n = len(ia)
    if n == 0:
        return (None, None, None)
    else:
        y = np.array(ia[1:] != ia[:-1])      # pairwise unequal (string safe)
        i = np.append(np.where(y), n - 1)    # include last element position
        z = np.diff(np.append(-1, i))        # run lengths
        p = np.cumsum(np.append(0, z))[:-1]  # positions

        return(z, p, ia[i])


def get_max_gap_size(y):
    """Give a series of binaries where True = Data Gap, find the largest gap by
    using run length encoding (rle)
    """

    rle_results = rle(y)
    gaps = rle_results[0][rle_results[2]]

    if len(gaps) > 0:
        max_gap_size = max(gaps)
    else:
        max_gap_size = 0

    return max_gap_size


def rolling_48hour_max_gap(contiguous_df):
    """
    Calculate the max gap size of the cgm trace in a 48 hour centered rolling
    window (where the evaluation point is in the center)

    Note: Centered window behavior keeps the evaluation point on the right side
    of the half-way point.

    e.g. In a window of 4: [elem1, elem2, elem3, elem4] - elem3 is the "center"
    """

    contiguous_df["rolling_48hour_max_gap"] = \
        contiguous_df["value"].rolling(
                window=288*2,
                min_periods=1,
                center=True).apply(lambda x:
                                   get_max_gap_size(np.isnan(x)),
                                   raw=True)

    return contiguous_df


def label_conditions(contiguous_df):
    """Labels each cgm entry as one of the 9 different conditions

    Condition # || 30min Median BG (mg/dL) & 15min Rate of Change (mg/dL/min)
                ||
        1       ||   [40-70) & < -1
        2       ||   [70-180] & < -1
        3       ||   (180-400] & < -1
        4       ||   [40-70) & [-1 to 1]
        5       ||   [70-180] & [-1 to 1]
        6       ||   (180-400] & [-1 to 1]
        7       ||   [40-70) & > 1
        8       ||   [70-180] & > 1
        9       ||   (180-400] & > 1
    """

    # Create boolean for each range and rate type
    contiguous_df["gte40_lt70"] = \
        (contiguous_df["rolling_30min_median"] >= 40) & \
        (contiguous_df["rolling_30min_median"] < 70)

    contiguous_df["gte70_lte180"] = \
        (contiguous_df["rolling_30min_median"] >= 70) & \
        (contiguous_df["rolling_30min_median"] <= 180)

    contiguous_df["gt180_lte400"] = \
        (contiguous_df["rolling_30min_median"] > 180) & \
        (contiguous_df["rolling_30min_median"] <= 400)

    contiguous_df["lt-1"] = \
        contiguous_df["rolling_15min_slope"] < -1

    contiguous_df["gte-1_lte1"] = \
        (contiguous_df["rolling_15min_slope"] >= -1) & \
        (contiguous_df["rolling_15min_slope"] <= 1)

    contiguous_df["gt1"] = \
        contiguous_df["rolling_15min_slope"] > 1

    # Set baseline condition to 0
    # Any 0's left over were cgm points
    # with a rate/range that could not be calculated
    contiguous_df["condition"] = 0

    # Create boolean array for each condition
    cond_1 = ((contiguous_df["gte40_lt70"]) & (contiguous_df["lt-1"]))
    cond_2 = ((contiguous_df["gte70_lte180"]) & (contiguous_df["lt-1"]))
    cond_3 = ((contiguous_df["gt180_lte400"]) & (contiguous_df["lt-1"]))
    cond_4 = ((contiguous_df["gte40_lt70"]) & (contiguous_df["gte-1_lte1"]))
    cond_5 = ((contiguous_df["gte70_lte180"]) & (contiguous_df["gte-1_lte1"]))
    cond_6 = ((contiguous_df["gt180_lte400"]) & (contiguous_df["gte-1_lte1"]))
    cond_7 = ((contiguous_df["gte40_lt70"]) & (contiguous_df["gt1"]))
    cond_8 = ((contiguous_df["gte70_lte180"]) & (contiguous_df["gt1"]))
    cond_9 = ((contiguous_df["gt180_lte400"]) & (contiguous_df["gt1"]))

    # Set each condition value to the boolean locations
    contiguous_df.loc[cond_1, "condition"] = 1
    contiguous_df.loc[cond_2, "condition"] = 2
    contiguous_df.loc[cond_3, "condition"] = 3
    contiguous_df.loc[cond_4, "condition"] = 4
    contiguous_df.loc[cond_5, "condition"] = 5
    contiguous_df.loc[cond_6, "condition"] = 6
    contiguous_df.loc[cond_7, "condition"] = 7
    contiguous_df.loc[cond_8, "condition"] = 8
    contiguous_df.loc[cond_9, "condition"] = 9

    return contiguous_df


def get_evaluation_points(contiguous_df):
    """
    Gets a evaluation points for each condition from the dataset if available
    """

    # Set window size of snapshot
    window_size = 288*2

    # Create bool of all values with a condition and max gap <= 15min
    qualified_bool = \
        (contiguous_df["condition"] > 0) & \
        (contiguous_df["rolling_48hour_max_gap"] <= 3)

    qualified_condition_list = \
        contiguous_df.loc[qualified_bool, "condition"].copy()

    evaluation_points = np.zeros(9)

    for condition in np.arange(1, 10):
        # Get the list of qualified locations for the condition
        condition_locations = \
            qualified_condition_list[
                    qualified_condition_list == condition
                    ].index

        # If no condition locations, skip loop to next condition
        if(len(condition_locations) == 0):
            continue

        # Randomly select one of the condition's locations
        random_loc = np.random.choice(condition_locations)

        # Add location to evaluation_points
        evaluation_points[condition - 1] = random_loc

        # Remove all locations within ± window_size-1 from qualified_locations
        # to prevent overlap when selecting the next condition snapshot
        overlapping_index = \
            np.arange(
                random_loc - (window_size-1),
                random_loc + (window_size-1)+1
                )

        index_to_drop = \
            set(overlapping_index) & set(qualified_condition_list.index)

        qualified_condition_list.drop(index=index_to_drop, inplace=True)

    return evaluation_points


def get_summary_results(file_name, contiguous_df, evaluation_points):
    """Create a summary of all results to store in a spreadsheet"""

    results = pd.DataFrame(index=[0])

    # Get counts for each rate, range, and condition
    results["file_name"] = file_name
    results["gte40_lt70"] = contiguous_df["gte40_lt70"].sum()
    results["gte70_lte180"] = contiguous_df["gte70_lte180"].sum()
    results["gt180_lte400"] = contiguous_df["gt180_lte400"].sum()
    results["lt-1"] = contiguous_df["lt-1"].sum()
    results["gte-1_lte1"] = contiguous_df["gte-1_lte1"].sum()
    results["gt1"] = contiguous_df["gt1"].sum()

    for num in range(10):
        results["cond" + str(num)] = sum(contiguous_df["condition"] == num)

    for num in range(9):
        # Append snapshot locations to dataframe
        results["cond"+str(num)+"_eval_loc"] = evaluation_points[num]

    return results


def main(data):
    """Main function calls"""

    # Separate CGM data
    cgm_df = data[data.type == "cbg"].copy()

    # Convert value from mmol/L to mg/dL
    cgm_df["value"] = cgm_df["value"] * 18.01559

    # Fit the CGM trace to a contiguous 5-minute time series to uncover gaps
    contiguous_df = create_5min_contiguous_df(cgm_df)

    # Calculate the median BG with a 30-minute rolling window
    contiguous_df = rolling_30min_median(contiguous_df)

    # Calculate the slope in mg/dL/min with a 15-minute rolling window
    contiguous_df = rolling_15min_slope(contiguous_df)

    # Apply one of the 9 conditions labels to each CGM point
    contiguous_df = label_conditions(contiguous_df)

    # Get the max gap size across 48-hour windows
    contiguous_df = rolling_48hour_max_gap(contiguous_df)

    # Get the locations of each evaluation point in a 48-hour snapshot
    evaluation_points = get_evaluation_points(contiguous_df)

    # Summarize results
    results = get_summary_results(file_name, contiguous_df, evaluation_points)

    return results


# %%
if __name__ == "__main__":
    file_name = "data.csv"
    file_location = "."

    file_path = os.path.join(file_location, file_name)
    data = import_data(file_path)

    main(data)
