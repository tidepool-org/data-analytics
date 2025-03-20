# -*- coding: utf-8 -*-
"""get_donor_data_and_metadata.py
In the context of the big data donation
project, this code grabs donor data and metadata.

This code calls accept_new_donors_and_get_donor_list.py
to get the most recent donor list
"""

# %% REQUIRED LIBRARIES
import pandas as pd
import datetime as dt
import numpy as np
import os
import sys
import getpass
import requests
import json
import pdb
import argparse
envPath = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if envPath not in sys.path:
    sys.path.insert(0, envPath)
import environmentalVariables

import get_donor_data.tidepool_api_bigdata as tpapi


# %% USER INPUTS (choices to be made in order to run the code)
codeDescription = "get donor metadata"
parser = argparse.ArgumentParser(description=codeDescription)

parser.add_argument(
    "-d",
    "--date-stamp",
    dest="date_stamp",
    default=dt.datetime.now().strftime("%Y-%m-%d"),
    help="date, in '%Y-%m-%d' format, of the date when " +
    "donors were accepted"
)

parser.add_argument(
    "-w",
    "--weeks-of-data",
    dest="weeks_of_data",
    type=int,
    default=52*10,
    help="enter the number of weeks of data you want to download"
)

parser.add_argument(
    "-dg",
    "--donor-group",
    dest="donor_group",
    default=np.nan,
    help="name of the donor group in the tidepool .env file"
)

parser.add_argument(
    "-u",
    "--userid",
    dest="userid_of_shared_user",
    default=np.nan,
    help="userid of account shared with the donor group or master account"
)

parser.add_argument(
    "-a",
    "--auth",
    dest="auth",
    default=np.nan,
    help="tuple that contains (email, password)"
)

parser.add_argument(
    "-e",
    "--email",
    dest="email",
    default=np.nan,
    help="email address of the master account"
)

parser.add_argument(
    "-p",
    "--password",
    dest="password",
    default=np.nan,
    help="password of the master account"
)

parser.add_argument(
    "-o",
    "--output-data-path",
    dest="data_path",
    default=os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "data"
        )
    ),
    help="the output path where the data is stored"
)

args = parser.parse_args()


# %% FUNCTIONS
def make_folder_if_doesnt_exist(folder_paths):
    ''' function requires a single path or a list of paths'''
    if not isinstance(folder_paths, list):
        folder_paths = [folder_paths]
    for folder_path in folder_paths:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
    return


def get_data_api(userid, startDate, endDate, headers):

    startDate = startDate.strftime("%Y-%m-%d") + "T00:00:00.000Z"
    endDate = endDate.strftime("%Y-%m-%d") + "T23:59:59.999Z"

    print(f"Downloading data between {startDate} and {endDate}")

    device_data_api_call = (
        "https://api.tidepool.org/data/" + userid + "?" +
        "endDate=" + endDate + "&" +
        "startDate=" + startDate + "&" +
        "dexcom=true" + "&" +
        "medtronic=true" + "&" +
        "carelink=true"
    )

    device_data_api_response = requests.get(device_data_api_call, headers=headers)
    if(device_data_api_response.ok):
        json_data = json.loads(device_data_api_response.content.decode())
        df = pd.DataFrame(json_data)
    else:
        raise Exception(f"ERROR in getting data between {startDate} and {endDate}. {device_data_api_response.status_code}")

    endDate = pd.to_datetime(startDate) - pd.Timedelta(1, unit="d")

    return df, endDate


def get_date_groups(start_date, end_date, num_groups=1):
    """
    Get non-overlapping groups of dates between a start and end date.
    """
    num_days_each_group = (end_date - start_date).days / num_groups

    if num_groups > 1:
        for i in range(num_groups - 1):
            yield (start_date + dt.timedelta(num_days_each_group * i), start_date + dt.timedelta(num_days_each_group*(i+1) - 1))
        yield (start_date + dt.timedelta(num_days_each_group * (num_groups-1)), end_date)
    else:
        yield (start_date, end_date)


def test_get_date_groups():
    """
    Basic logic tests for date groupings used to break up api calls
    """

    test_start_date = dt.datetime(2013, 1, 1)
    test_end_date = dt.datetime(2025, 1, 1)

    for num_groups in range(1, 20):
        groups = list(get_date_groups(test_start_date, test_end_date, num_groups=num_groups))

        grp_ctr = 0

        assert groups[0][0] == test_start_date
        assert groups[-1][-1] == test_end_date

        # Last date in each group is one day before first date in each group
        for i, (group_start_date, group_end_date) in enumerate(groups):
            if i > 0:
                assert (groups[i][0] - groups[i-1][1]).days == 1  # groups are 1 day apart
            grp_ctr += 1

        assert grp_ctr == num_groups  # groups are the expected number


def get_data(
    weeks_of_data=10*52,
    donor_group="",
    userid_of_shared_user=np.nan,
):

    print("\tGetting user data...")
    username, password = environmentalVariables.get_environmental_variables(donor_group)

    endDate = pd.to_datetime("now") + pd.Timedelta(1, unit="d")
    startDate = pd.to_datetime(endDate) - pd.Timedelta(weeks_of_data*7, "d")

    # max_retries = 4
    num_retries = 0
    date_groups = get_date_groups(startDate, endDate, num_groups=100)

    df = pd.DataFrame()
    while True:
        try:
            for start_date_chunk, end_date_chunk in date_groups:
                access_token = tpapi.retrieve_existing_token(username=username, password=password)
                headers = {
                    "x-tidepool-session-token": access_token,
                    "Content-Type": "application/json"
                }

                df_chunk, _ = get_data_api(
                    userid_of_shared_user,
                    start_date_chunk,
                    end_date_chunk,
                    headers
                )
                df = pd.concat([df, df_chunk], axis=0)

            break
        except Exception:
            num_retries += 1
            # date_groups = list(get_date_groups(start_date_chunk, endDate, num_groups=num_retries))
            print(f"Exception getting data for user. Trying again. Num retries: {num_retries}")
            break

    print("\tFinished getting user data.")
    return df, userid_of_shared_user


# %% START OF CODE
def get_and_save_dataset(
    date_stamp=args.date_stamp,
    data_path=args.data_path,
    weeks_of_data=args.weeks_of_data,
    donor_group=args.donor_group,
    userid_of_shared_user=args.userid_of_shared_user,
    auth=args.auth,
    email=args.email,
    password=args.password
):
    # create output folders if they don't exist
    phi_date_stamp = "PHI-" + date_stamp
    donor_folder = os.path.join(data_path,  f"{phi_date_stamp}-donor-data")

    dataset_path = os.path.join(donor_folder, f"{phi_date_stamp}-csvData")
    make_folder_if_doesnt_exist(dataset_path)

    # get dataset
    data, userid = get_data(weeks_of_data, donor_group, userid_of_shared_user)

    # save data
    dataset_output_path = os.path.join(dataset_path, f"PHI-{userid}.csv")

    data.to_csv(dataset_output_path)


if __name__ == "__main__":

    test_get_date_groups()

    # get_and_save_dataset(
    #     date_stamp=args.date_stamp,
    #     data_path=args.data_path,
    #     weeks_of_data=args.weeks_of_data,
    #     donor_group=args.donor_group,
    #     userid_of_shared_user=args.userid_of_shared_user,
    #     auth=args.auth,
    #     email=args.email,
    #     password=args.password
    # )
