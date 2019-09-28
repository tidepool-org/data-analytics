# -*- coding: utf-8 -*-
"""
aggregates cgm stats by person, age, years-living-with (ylw) diabetes,
and age-ylw

date: 09/2019
authors: ed nykaza & anne evered
"""

# %% REQUIRED LIBRARIES
import numpy as np
import pandas as pd
import os
import sys
import argparse
from numpy.linalg import pinv
get_donor_data_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
if get_donor_data_path not in sys.path:
    sys.path.insert(0, get_donor_data_path)
from get_donor_data.get_single_tidepool_dataset_json import (
    make_folder_if_doesnt_exist
)


# %% FUNCTIONS
def get_percent(x):
    percent_ = np.nansum(x) / np.sum(~np.isnan(x))
    return percent_


def add_user_stats(cgm_ts_df, group_by_categories, category_name):
    df = cgm_ts_df.groupby(group_by_categories)["mg/dL"].describe(
        percentiles=[0.10, 0.25, 0.50, 0.75, 0.90]
    )

    df["startDateTime"] = (
        cgm_ts_df.groupby(group_by_categories)["roundedUtcTime"].min()
    )
    df["endDateTime"] = (
        cgm_ts_df.groupby(group_by_categories)["roundedUtcTime"].max()
    )
    df["category"] = category_name
    df['group_by_values'] = df.index
    df['category_value'] = (
        cgm_ts_df.groupby(group_by_categories)[group_by_categories[0]].max()
    )
    df['mean'] = cgm_ts_df.groupby(group_by_categories)["mg/dL"].mean()
    # GMI(%) = 3.31 + 0.02392 x [mean glucose in mg/dL]
    df["gmi"] = (3.31 + (0.02392 * df['mean']))
    df['std'] = cgm_ts_df.groupby(group_by_categories)["mg/dL"].std()
    df['cv'] = (
        cgm_ts_df.groupby(group_by_categories)["mg/dL"].mean()
        / cgm_ts_df.groupby(group_by_categories)["mg/dL"].std()
    )

    cgm_cats = [
        'cgm < 40', 'cgm >= 40', 'cgm < 54', 'cgm >= 54',
        'cgm < 70', 'cgm >= 70', 'cgm <= 140', 'cgm > 140',
        'cgm <= 180', 'cgm > 180', 'cgm <= 250', 'cgm > 250',
        'cgm <= 300', 'cgm > 300', 'cgm <= 400', 'cgm > 400',
        '40 <= cgm < 54', '54 <= cgm < 70', '70 <= cgm <= 140',
        '70 <= cgm <= 180', '180 < cgm <= 250',
        '250 < cgm <= 400'
    ]

    for cgm_cat in cgm_cats:

        df["percent." + cgm_cat] = (
            cgm_ts_df.groupby(
                group_by_categories
            )[cgm_cat].apply(get_percent)
        ) * 100

    if cgm_ts_df["age"].notnull().sum() > 2:
        df["age"] = cgm_ts_df.groupby(group_by_categories)["age"].median()
    else:
        df["age"] = np.nan

    if cgm_ts_df["ylw"].notnull().sum() > 2:
        df["ylw"] = cgm_ts_df.groupby(group_by_categories)["ylw"].median()
    else:
        df["ylw"] = np.nan

    for lt_threshold in [40, 54, 70]:
        n_episodes_lt = (
            cgm_ts_df.groupby(
                group_by_categories
            )["episode.cgm < {}.durationThreshold=5.episodeStart".format(
                lt_threshold
            )].sum()
        ) * 1

        df["count.episode.cgm < {}".format(lt_threshold)] = n_episodes_lt

        total_time_in_episodes_lt = (
            cgm_ts_df.groupby(
                group_by_categories
            )["episode.cgm < {}.durationThreshold=5.isEpisode".format(
                lt_threshold
            )].sum()
        ) * 5

        avg_episode_lt = total_time_in_episodes_lt / n_episodes_lt
        df["avgDuration.episode.cgm < {}".format(lt_threshold)] = (
            avg_episode_lt
        )

    return df


def get_slope(last_3_mg_dL):

    y = np.array(last_3_mg_dL)

    time_matrix = np.array([
    	[5, 1],
    	[10, 1],
    	[15, 1],
    ])

    b = pinv(time_matrix.T.dot(time_matrix)).dot(time_matrix.T).dot(y)
    slope = np.round(b[0], 1)

    return slope


def get_bg_test_matrix_info(all_cgm):
    # work with all of the non-null data, even 39 = LOW and 401 = HIGH
    ts39_401 = all_cgm["mg/dL"].copy()

    # derfine the windows to calculate the stats over
    window_names = ["last3", "last6"]
    window_lengths = [3, 6]

    for w_name, w_len in zip(window_names, window_lengths):
        # NOTE: these calculations only require 3 points to make
        roll39_401 = ts39_401.rolling(min_periods=3, window=w_len)
        #  get the rate of the last 3
        if "last3" in w_name:
            all_cgm[w_name + ".slope"] = roll39_401.apply(get_slope, raw=True)
            all_cgm[w_name + ".slope"] < -1

            all_cgm["last3cgmRate < -1"] = all_cgm[w_name + ".slope"] < -1

            all_cgm["-1 <= last3cgmRate <= 1"] = (
                (all_cgm[w_name + ".slope"] >= -1)
                & (all_cgm[w_name + ".slope"] <= 1)
            )

            all_cgm["last3cgmRate > 1"] = all_cgm[w_name + ".slope"] > 1

        else:
            # get the median of the last 6
            all_cgm[w_name + ".median"] = roll39_401.median()

            all_cgm["40 <= last6cgm < 70"] = (
                (all_cgm[w_name + ".median"] >= 40)
                & (all_cgm[w_name + ".median"] < 70)
            )

            all_cgm["70 <= last6cgm <= 180"] = (
                (all_cgm[w_name + ".median"] >= 70)
                & (all_cgm[w_name + ".median"] <= 180)
            )

            all_cgm["180 < last6cgm <= 400"] = (
                (all_cgm[w_name + ".median"] > 180)
                & (all_cgm[w_name + ".median"] <= 400)
            )

    bg_test_matrix_rates = [
        "last3cgmRate < -1", "-1 <= last3cgmRate <= 1", "last3cgmRate > 1"
    ]

    bg_test_matrix_values = [
        "40 <= last6cgm < 70", "70 <= last6cgm <= 180", "180 < last6cgm <= 400"
    ]

    hashid = all_cgm.loc[all_cgm["hashid"].notnull(), "hashid"].unique()[0]
    bg_cond = pd.DataFrame(index=[hashid])
    for c1 in bg_test_matrix_rates:
        for c2 in bg_test_matrix_values:
            condition_name = "{} & {}".format(c1, c2)
            all_cgm[condition_name] = ((all_cgm[c1]) & (all_cgm[c2]))

            temp_bg_cond = add_user_stats(
                all_cgm.copy(),
                [condition_name],
                condition_name
            )

            if True in temp_bg_cond.index:
                temp_count, temp_per_lt_54 = (
                    temp_bg_cond.loc[
                        True,
                        ["count", "percent.cgm < 54"]
                    ].values
                )
                bg_cond["count." + condition_name] = temp_count
                bg_cond["percent_lt_54." + condition_name] = temp_per_lt_54

            else:
                bg_cond["count." + condition_name] = np.nan
                bg_cond["percent_lt_54." + condition_name] = np.nan

    return bg_cond


# %% MAIN FUNCTION
def get_aggregate_cgm_stats(cgm_stats_file_name, save_path):
    user_stats_df = pd.DataFrame(
        columns=[
            'category', 'category_value', 'group_by_values',
            'startDateTime', 'endDateTime', 'age', 'ylw',
            'count', 'mean', 'gmi', 'std', 'cv',
            'min', '10%', '25%', '50%', '75%', '90%', 'max'
        ]
    )

    make_folder_if_doesnt_exist([save_path])

    cgm_series = pd.read_csv(cgm_stats_file_name, low_memory=False)
    hashid = cgm_series.loc[
        cgm_series["hashid"].notnull(),
        "hashid"
    ].unique()[0]

    save_file_path = os.path.join(save_path, hashid + ".csv.gz")

    if pd.notnull(cgm_series.age).sum() > 0:
        age_string = cgm_series["age"].astype(str)
        ylw_string = cgm_series["ylw"].astype(str)
        cgm_series["age-ylw"] = age_string + "-" + ylw_string
        person_df = add_user_stats(cgm_series.copy(), ["hashid"], "person")
        condition_df = get_bg_test_matrix_info(cgm_series.copy())
        person_df = pd.concat(
            [person_df, condition_df],
            axis=1
        )

        looper_df = add_user_stats(
            cgm_series.copy(),
            ["isLoopDay", "hashid"],
            "isLoopDay"
        )

        age_df = add_user_stats(cgm_series.copy(), ["age", "hashid"], "age")

        if pd.notnull(cgm_series.ylw).sum() > 0:
            ylw_df = add_user_stats(
                cgm_series.copy(),
                ["ylw", "hashid"],
                "ylw"
            )
            age_ylw_df = add_user_stats(
                cgm_series.copy(),
                ["age-ylw", "hashid"],
                "age-ylw"
            )
        else:
            ylw_df = pd.DataFrame()
            age_ylw_df = pd.DataFrame()

        user_stats_df = pd.concat(
            [user_stats_df, person_df, age_df, ylw_df, age_ylw_df, looper_df],
            ignore_index=True,
            sort=False
        )

        print("done with donor {}".format(hashid))
    else:
        print("skipping donor {} bc no age data".format(hashid))

    user_stats_df.to_csv(save_file_path)

    return user_stats_df


# %% MAIN
if __name__ == "__main__":
    # USER INPUTS (choices to be made in order to run the code)
    codeDescription = "get aggregate cgm stats for donor data"
    parser = argparse.ArgumentParser(description=codeDescription)

    parser.add_argument(
        "-i",
        "--input-json-data-path",
        dest="cgm_file_path",
        default=os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), "..", "data",
                "PHI-2019-07-17-donor-data",
                "PHI-2019-07-17-cgm-stats",
                "PHI-10623efdc6-cgm-stats.csv.gz"
            )
        ),
        help="the path where the cgm stats data is located"
    )

    parser.add_argument(
        "-o",
        "--output-data-path",
        dest="data_path",
        default=os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), "..", "data",
                "PHI-2019-07-17-donor-data",
                "2019-07-17-aggregate-cgm-stats"
            )
        ),
        help="the output path where the data is stored"
    )

    args = parser.parse_args()

    # the main function
    get_aggregate_cgm_stats(
        cgm_stats_file_name=args.cgm_file_path,
        save_path=args.data_path,
    )
