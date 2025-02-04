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
        sys.exit(f"ERROR in getting data between {startDate} and {endDate}. {device_data_api_response.status_code}")

    endDate = pd.to_datetime(startDate) - pd.Timedelta(1, unit="d")

    return df, endDate


def get_data(
    weeks_of_data=10*52,
    donor_group="",
    userid_of_shared_user=np.nan,
):

    print("\tGetting user data...")
    auth = environmentalVariables.get_environmental_variables(donor_group)

    username, password = auth
    access_token = tpapi.retrieve_existing_token(username=username, password=password)
    headers = {
        "x-tidepool-session-token": access_token,
        "Content-Type": "application/json"
    }

    endDate = pd.to_datetime("now") + pd.Timedelta(1, unit="d")
    startDate = pd.to_datetime(endDate) - pd.Timedelta(weeks_of_data*7, "d")

    df, _ = get_data_api(
        userid_of_shared_user,
        startDate,
        endDate,
        headers
        )

    tpapi.logout(username, password)

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
    get_and_save_dataset(
        date_stamp=args.date_stamp,
        data_path=args.data_path,
        weeks_of_data=args.weeks_of_data,
        donor_group=args.donor_group,
        userid_of_shared_user=args.userid_of_shared_user,
        auth=args.auth,
        email=args.email,
        password=args.password
    )
