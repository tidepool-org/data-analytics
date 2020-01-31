#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch iCGM Condition Stats
===========================
:File: batch-icgm-condition-stats.py
:Description: A batch processing script for the icgm_condition_finder.py module
              Given a folder of Tidepool datasets, get a summary of all results
              using the condition finder script.
:Version: 0.0.1
:Created: 2020-01-30
:Authors: Jason Meno (jam)
:Dependencies: A folder of .csvs containing Tidepool CGM device data
:License: BSD-2-Clause
"""
import pandas as pd
import icgm_condition_finder
import time
import datetime as dt
import os
from multiprocessing import Pool, cpu_count
import traceback
import sys
# %%

data_location = "data_folder/"
file_list = os.listdir(data_location)

# Filter only files with .csv in their name (includes .csv.gz files)
file_list = [filename for filename in file_list if '.csv' in filename]

# %%


def get_icgm_condition_stats(file_name, data_location, user_loc):

    file_path = data_location + file_name
    # print(str(user_loc) + " STARTING")
    if((user_loc % 100 == 0) & (user_loc > 99)):
        print(user_loc)
        log_file = open('batch-icgm-condition-stats-log.txt', 'a')
        log_file.write(str(user_loc)+"\n")
        log_file.close()

    results = icgm_condition_finder.get_empty_results_frame()
    results['file_name'] = file_name

    try:
        df = pd.read_csv(file_path, low_memory=False)

        if 'type' in set(df):
            if 'cbg' in set(df['type']):
                results = icgm_condition_finder.main(df, file_name)
                results['status'] = "Complete"
            else:
                results['status'] = "No CGM Data"
        else:
            results['status'] = "Empty Dataset"

    except Exception as e:
        df = pd.DataFrame()
        print("Processing Failed For: " + file_path)
        exception_text = "Failed - " + str(e)
        results['status'] = "Failed"
        results['exception_text'] = exception_text

    return results


# %%
if __name__ == "__main__":
    # Start Pipeline
    start_time = time.time()

    # Startup CPU multiprocessing pool
    pool = Pool(int(cpu_count()))

    pool_array = [pool.apply_async(
            get_icgm_condition_stats,
            args=[file_list[user_loc],
                  data_location,
                  user_loc
                  ]
            ) for user_loc in range(len(file_list))]

    pool.close()
    pool.join()

    end_time = time.time()
    elapsed_minutes = (end_time - start_time)/60
    elapsed_time_message = "Batch iCGM Condition Stats completed in: " + \
        str(elapsed_minutes) + " minutes\n"
    print(elapsed_time_message)
    log_file = open('batch-icgm-condition-stats-log.txt', 'a')
    log_file.write(str(elapsed_time_message)+"\n")
    log_file.close()

    # %% Append results of each pool into an array

    results_array = []

    for result_loc in range(len(pool_array)):
        try:
            results_array.append(pool_array[result_loc].get())
        except Exception as e:
            print('Failed to get results! ' + str(e))
            exception_text = traceback.format_exception(*sys.exc_info())
            print('\nException Text:\n')
            for text_string in exception_text:
                print(text_string)

    # %%
    # Convert results into dataframe
    icgm_condition_summary_df = pd.concat(results_array, sort=False)
    today_timestamp = dt.datetime.now().strftime("%Y-%m-%d")
    results_export_filename = \
        'PHI-batch-icgm-condition-stats-' + \
        today_timestamp + \
        '.csv'
    icgm_condition_summary_df.to_csv(results_export_filename, index=False)
