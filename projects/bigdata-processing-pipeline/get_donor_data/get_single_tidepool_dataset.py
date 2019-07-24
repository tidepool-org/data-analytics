# -*- coding: utf-8 -*-
"""get_donor_data_and_metadata.py
In the context of the big data donation
project, this code grabs donor data and metadata.

This code calls accept_new_donors_and_get_donor_list.py
to get the most recent donor list
"""

# %% REQUIRED LIBRARIES
try:
    from get_single_dataset_info import expand_data, save_df
except:
    from get_donor_data.get_single_dataset_info import expand_data, save_df
import pandas as pd
import datetime as dt
import numpy as np
import os
import sys
import getpass
import requests
import json
import argparse
envPath = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if envPath not in sys.path:
    sys.path.insert(0, envPath)
import environmentalVariables


# %% FUNCTIONS
def get_data_api(userid, startDate, endDate, headers):

    startDate = startDate.strftime("%Y-%m-%d") + "T00:00:00.000Z"
    endDate = endDate.strftime("%Y-%m-%d") + "T23:59:59.999Z"

    api_call = (
        "https://api.tidepool.org/data/" + userid + "?" +
        "endDate=" + endDate + "&" +
        "startDate=" + startDate + "&" +
        "dexcom=true" + "&" +
        "medtronic=true" + "&" +
        "carelink=true"
    )

    api_response = requests.get(api_call, headers=headers)
    if(api_response.ok):
        json_data = json.loads(api_response.content.decode())
        df = pd.DataFrame(json_data)
        print("getting data between %s and %s" % (startDate, endDate))

    else:
        sys.exit(
            "ERROR in getting data between %s and %s" % (startDate, endDate),
            api_response.status_code
        )

    endDate = pd.to_datetime(startDate) - pd.Timedelta(1, unit="d")

    return df, endDate


def get_data(
    weeks_of_data=10*52,
    donor_group=np.nan,
    userid=np.nan,
    auth=np.nan,
    email=np.nan,
    password=np.nan,
):
    # login
    if pd.notnull(donor_group):
        if donor_group == "bigdata":
            dg = ""
        else:
            dg = donor_group

        auth = environmentalVariables.get_environmental_variables(dg)

    if pd.isnull(auth):
        if pd.isnull(email):
            email = input("Enter Tidepool email address:\n")

        if pd.isnull(password):
            password = getpass.getpass("Enter password:\n")

        auth = (email, password)

    api_call = "https://api.tidepool.org/auth/login"
    api_response = requests.post(api_call, auth=auth)
    if(api_response.ok):
        xtoken = api_response.headers["x-tidepool-session-token"]
        userid_master = json.loads(api_response.content.decode())["userid"]
        headers = {
            "x-tidepool-session-token": xtoken,
            "Content-Type": "application/json"
        }
    else:
        sys.exit("Error with " + auth[0] + ":" + str(api_response.status_code))

    if pd.isnull(userid):
        userid = userid_master
        print(
            "getting data for the master account since no shared " +
            "user account was given"
        )

    print("logging into", auth[0], "...")

    # download user data
    print("downloading data ...")
    df = pd.DataFrame()
    endDate = pd.datetime.now() + pd.Timedelta(1, unit="d")

    if weeks_of_data > 52:
        years_of_data = int(np.floor(weeks_of_data/52))

        for years in range(0, years_of_data + 1):
            startDate = pd.datetime(
                endDate.year - 1,
                endDate.month,
                endDate.day + 1
            )
            year_df, endDate = get_data_api(
                userid,
                startDate,
                endDate,
                headers
            )

            df = pd.concat(
                [df, year_df],
                ignore_index=True,
                sort=False
            )

    else:
        startDate = (
            pd.to_datetime(endDate) - pd.Timedelta(weeks_of_data*7, "d")
        )

        df, _ = get_data_api(
            userid,
            startDate,
            endDate,
            headers
            )

    # logout
    api_call = "https://api.tidepool.org/auth/logout"
    api_response = requests.post(api_call, auth=auth)

    if(api_response.ok):
        print("successfully logged out of", auth[0])

    else:
        sys.exit(
            "Error with logging out for " +
            auth[0] + ":" + str(api_response.status_code)
        )

    return df, userid


# %% START OF CODE
def get_and_save_dataset(
    date_stamp,
    data_path,
    weeks_of_data,
    donor_group,
    userid,
    auth,
    email,
    password,
    expand_dataset
):

    # get dataset
    data, userid = get_data(
        weeks_of_data=weeks_of_data,
        donor_group=donor_group,
        userid=userid,
        auth=auth,
        email=email,
        password=password
    )

    # if the there is data
    if len(data) > 1:
        # save data
        print("saving csv data...")
        _ = save_df(
                data,
                userid=userid,
                data_path=data_path,
                date_stamp=date_stamp,
                folder_name="csvData",
                phi=True
        )

        # get dataset info
        if expand_dataset:
            summary_df, expanded_df = expand_data(data)
            print("saving summary data...")
            _ = save_df(
                summary_df,
                userid=userid,
                data_path=data_path,
                date_stamp=date_stamp,
                folder_name="datasetSummary",
                phi=True,
                name_suffix="-datasetSummary"
            )

            # save expanded data
            print("saving expanded data...")
            _ = save_df(
                expanded_df,
                userid=userid,
                data_path=args.data_path,
                date_stamp=args.date_stamp,
                folder_name="expandedData",
                phi=True,
                name_suffix="-expandedData"
            )
    else:
        print("{} has no data".format(userid))


if __name__ == "__main__":
    # USER INPUTS (choices to be made in order to run the code)
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
        dest="userid",
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

    parser.add_argument(
        "-ex",
        "--expand-dataset",
        dest="expand_dataset",
        default=True,
        help=(
            "specify if you want to get/save the expanded datafram (True/False)"
            + "NOTE: this process is time consuming"
        )
    )

    args = parser.parse_args()

    # the main function
    get_and_save_dataset(
        date_stamp=args.date_stamp,
        data_path=args.data_path,
        weeks_of_data=args.weeks_of_data,
        donor_group=args.donor_group,
        userid=args.userid,
        auth=args.auth,
        email=args.email,
        password=args.password,
        expand_dataset=args.expand_dataset
    )
