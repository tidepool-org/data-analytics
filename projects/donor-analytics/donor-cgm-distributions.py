#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CGM Values & Rate of Change Distributions
=========================================
:File: donor-cgm-distributions.py
:Description: Batch processes distributions for CGM values and rate of change
:Version: 0.0.1
:Created: 2020-04-26
:Authors: Jason Meno (jameno)
:Dependencies: A folder containing .csvs downloaded from Tidepool API
:License: BSD-2-Clause
"""

import pandas as pd
import numpy as np
import os
import time
import multiprocessing as mp
import datetime
import traceback
import sys

# %%


def create_contiguous_data(cgm_df):

    # Convert and round time field to nearest 5min
    cgm_df["rounded_time"] = pd.to_datetime(cgm_df["time"], utc=True).dt.ceil(
        freq="5min"
    )

    contiguous_ts = pd.date_range(
        cgm_df.rounded_time.min(), cgm_df.rounded_time.max(), freq="5min"
    )

    cgm_df["join_reference"] = (
        cgm_df["rounded_time"] - cgm_df["rounded_time"].min()
    ).astype(int)
    cgm_df.set_index("join_reference", inplace=True)

    contiguous_df = pd.DataFrame(contiguous_ts, columns=["rounded_time"])
    contiguous_df["join_reference"] = (
        contiguous_df["rounded_time"] - cgm_df["rounded_time"].min()
    ).astype(int)
    contiguous_df.set_index("join_reference", inplace=True)

    cgm_df.drop(columns=["rounded_time"], inplace=True)
    contiguous_df = contiguous_df.join(cgm_df, on="join_reference", how="left")
    contiguous_df.reset_index(drop=True, inplace=True)

    # Sort by rounded time and uploadId (newest uploadId first)
    contiguous_df.sort_values(
        by=["rounded_time", "uploadId"], ascending=[False, False], inplace=True
    )

    # Drop duplicates, keeping the first (most recent upload) entry
    contiguous_df.drop_duplicates("rounded_time", keep="first", inplace=True)

    # Restore ascending timeseries
    contiguous_df.sort_values(by=["rounded_time"], ascending=True, inplace=True)
    contiguous_df = contiguous_df.reset_index(drop=True)

    return contiguous_df


def calc_age_and_ylw(birthdate, diagnosis_date, relative_date):

    # Calculate age and ylw
    if type(birthdate) == float:
        age = np.nan
    else:
        birthdate = pd.to_datetime(birthdate, utc=True)

        if birthdate.year > datetime.datetime.now().year:
            birthdate = birthdate.replace(year=birthdate.year - 100)

        age = int(np.floor((relative_date - birthdate).days / 365))

    if type(diagnosis_date) == float:
        ylw = np.nan
    else:
        diagnosis_date = pd.to_datetime(diagnosis_date, utc=True)

        if diagnosis_date.year > datetime.datetime.now().year:
            diagnosis_date = diagnosis_date.replace(year=diagnosis_date.year - 100)

        ylw = int(np.floor((relative_date - diagnosis_date).days / 365))

    return age, ylw


def add_metadata(contiguous_df, value_counts, diff_counts, metadata):

    file_name = metadata["file_name"]
    birthdate = metadata["birthday"]
    diagnosis_date = metadata["diagnosisDate"]
    diagnosisType = metadata["diagnosisType"]
    biologicalSex = metadata["biologicalSex"]

    start_date = contiguous_df["rounded_time"].min()
    end_date = contiguous_df["rounded_time"].max()

    start_age, start_ylw = calc_age_and_ylw(birthdate, diagnosis_date, start_date)
    end_age, end_ylw = calc_age_and_ylw(birthdate, diagnosis_date, end_date)

    metadata_list = [
        file_name,
        start_age,
        end_age,
        start_ylw,
        end_ylw,
        diagnosisType,
        biologicalSex,
    ]
    metadata_index = [
        "file_name",
        "start_age",
        "end_age",
        "start_ylw",
        "end_ylw",
        "diagnosis_type",
        "biological_sex",
    ]
    metadata_to_append = pd.DataFrame(metadata_list, index=metadata_index)

    value_counts = pd.concat([metadata_to_append.T, value_counts], axis=1)
    diff_counts = pd.concat([metadata_to_append.T, diff_counts], axis=1)

    return value_counts, diff_counts


def calc_cgm_distributions(cgm_df, file_name, metadata):

    print(file_name)
    contiguous_df = create_contiguous_data(cgm_df)
    value_counts = pd.DataFrame(contiguous_df["value"].value_counts()).T.reset_index(
        drop=True
    )
    diff_counts = pd.DataFrame(
        contiguous_df["value"].diff().value_counts()
    ).T.reset_index(drop=True)
    value_counts, diff_counts = add_metadata(
        contiguous_df, value_counts, diff_counts, metadata
    )

    return value_counts, diff_counts


def import_and_process(metadata, file_loc):
    # print(file_loc)
    file_name = metadata["file_name"]
    data_df = []
    value_counts = pd.DataFrame([{"file_name": file_name}])
    diff_counts = value_counts.copy()

    if (file_loc % 100 == 0) & (file_loc > 99):
        print(file_loc, "/", len(file_list))
        log_file = open("batch-donor-cgm_distributions-log.txt", "a")
        log_file.write(str(file_loc) + "/" + str(len(file_list)) + "\n")
        log_file.close()

    try:
        data_df = pd.read_csv(data_location + file_name, low_memory=False)

    except Exception as e:
        error = file_name + " failed to load!\n\n" + e.message + "\n\n"
        log_file = open("batch-donor-cgm_distributions-log.txt", "a")
        log_file.write(error)
        log_file.close()

    if len(data_df) > 0:
        # Check if cgm data is in dataframe
        if "cbg" in data_df["type"].values:
            cgm_df = data_df.loc[
                data_df["type"] == "cbg", ["time", "value", "uploadId"]
            ]
            del data_df
            cgm_df["value"] = (cgm_df["value"] * 18.01559).round().astype(int)
            value_counts, diff_counts = calc_cgm_distributions(
                cgm_df, file_name, metadata
            )

    return value_counts, diff_counts


# %%

if __name__ == "__main__":

    data_location = '/mnt/jasonmeno/donor-data-pipeline/src/PHI-2020-04-18-csvData/'
    metadata_location = '/mnt/jasonmeno/donor-data-pipeline/src/PHI-batch-metadata-2020-04-27.csv'

    file_list = os.listdir(data_location)

    # Filter only .csv files
    file_list = [filename for filename in file_list if ".csv" in filename]

    # Get metadata
    metadata_df = pd.read_csv(metadata_location, low_memory=False)
    metadata_df["file_name"] = "PHI-" + metadata_df["userid"] + ".csv.gz"
    metadata_df = metadata_df[
        ["file_name", "birthday", "diagnosisDate", "diagnosisType", "biologicalSex"]
    ]
    metadata_df = metadata_df[metadata_df["file_name"].isin(file_list)]

    start_time = time.time()

    # Startup CPU multiprocessing pool
    pool = mp.Pool(mp.cpu_count())
    pool_array = [
        pool.apply_async(
            import_and_process, args=[metadata_df.loc[file_loc], file_loc]
        )
        for file_loc in range(len(file_list))
    ]
    pool.close()
    pool.join()

    value_distributions = []
    diff_distributions = []

    # Append results of each pool into an array
    for result_loc in range(len(pool_array)):
        try:
            pool_result = pool_array[result_loc].get()
            value_distributions.append(pool_result[0])
            diff_distributions.append(pool_result[1])
        except Exception as e:
            print("Failed to get results for", file_list[result_loc])
            exception_text = str(e)
            print("\nException Text:\n")
            print(exception_text)

    # Convert results into dataframes and sort columns
    value_distributions_df = pd.concat(value_distributions, sort=False)
    sorted_value_columns = list(value_distributions_df.columns[:7]) + list(
        np.sort(value_distributions_df.columns[7:])
    )
    value_distributions_df = value_distributions_df[sorted_value_columns]
    diff_distributions_df = pd.concat(diff_distributions, sort=False)
    sorted_diff_columns = list(diff_distributions_df.columns[:7]) + list(
        np.sort(diff_distributions_df.columns[7:])
    )
    diff_distributions_df = diff_distributions_df[sorted_diff_columns]

    # %%

    today_timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
    value_dist_filename = (
        "PHI-donor-cgm-value-distributions-" + today_timestamp + ".csv"
    )
    value_distributions_df.to_csv(value_dist_filename, index=False)

    diff_dist_filename = "PHI-donor-cgm-diff-distributions-" + today_timestamp + ".csv"
    diff_distributions_df.to_csv(diff_dist_filename, index=False)

    # Close file and write runtime to log
    end_time = time.time()
    elapsed_minutes = (end_time - start_time) / 60
    elapsed_time_message = (
        "Processed "
        + str(len(file_list))
        + " csv files in "
        + str(elapsed_minutes)
        + " minutes\n"
    )
    log_file = open("batch-donor-cgm_distributions-log.txt", "a")
    log_file.write(elapsed_time_message)
    log_file.close()
