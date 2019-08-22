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
import time
import getpass
import requests
import json
import argparse
import pdb
envPath = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if envPath not in sys.path:
    sys.path.insert(0, envPath)
import environmentalVariables

# %% GLOBAL VARIABLES
current_date = dt.datetime.now().strftime("%Y-%m-%d")

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
        print("getting data between %s and %s" % (startDate, endDate))
        json_data = json.loads(api_response.content.decode())

    else:
        sys.exit(
            "ERROR in getting data between %s and %s" % (startDate, endDate),
            api_response.status_code
        )

    endDate = pd.to_datetime(startDate) - pd.Timedelta(1, unit="d")

    return json_data, endDate


def get_data(
        weeks_of_data=10*52,
        save_data_path=os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "data",
                "PHI-" + current_date + "-donor-data",
                "PHI-" + current_date + "-jsonData",
            )
        ),
        overwrite_hours=24,
        donor_group=np.nan,
        userid=np.nan,
        auth=np.nan,
        email=np.nan,
        password=np.nan,
        save_file="False",
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
    print("downloading data for {} ...".format(userid))
    endDate = pd.datetime.now() + pd.Timedelta(1, unit="d")

    output_folder = os.path.join(
        save_data_path,
        "PHI-" + userid,
    )

    output_file_path = os.path.join(
        output_folder,
        "PHI-{}.json".format(userid)
    )

    download_ = True
    for f in [output_folder, output_file_path]:
        path_exist = os.path.exists(f)
        if path_exist:
            last_save = os.path.getmtime(f)
            time_threshold = time.time() - (overwrite_hours * 3600)
            within_time_threshold = last_save > time_threshold
            if within_time_threshold:
                download_ = False

    if download_:

        big_json_file = []

        if weeks_of_data > 52:
            years_of_data = int(np.floor(weeks_of_data/52))

            for years in range(0, years_of_data + 1):
                startDate = pd.datetime(
                    endDate.year - 1,
                    endDate.month,
                    endDate.day + 1
                )
                json_data, endDate = get_data_api(
                    userid,
                    startDate,
                    endDate,
                    headers
                )

                big_json_file = big_json_file + json_data

        else:
            startDate = (
                pd.to_datetime(endDate) - pd.Timedelta(weeks_of_data*7, "d")
            )

            json_data, _ = get_data_api(
                userid,
                startDate,
                endDate,
                headers
                )

            big_json_file = big_json_file + json_data

        # save data
        if len(big_json_file) > 1:
            if "T" in str(save_file).upper():
                make_folder_if_doesnt_exist(output_folder)
                print("saving data for {}".format(userid))
                with open(output_file_path, 'w') as outfile:
                    json.dump(big_json_file, outfile)
            else:
                print("{} has data, but will not be saved".format(userid))
        else:
            print("{} has no data".format(userid))

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
    else:
        print(
            "skipping bc {}'s data was downloaded (attempted)".format(userid)
            + " within the last {} hours".format(overwrite_hours)
        )

    if "T" in str(save_file).upper():
        return np.nan, userid
    else:
        df = pd.DataFrame(big_json_file)
        return df, userid


# %% MAIN
if __name__ == "__main__":
    # USER INPUTS (choices to be made in order to run the code)
    codeDescription = "get donor json file"
    parser = argparse.ArgumentParser(description=codeDescription)

    parser.add_argument(
        "-o",
        "--output-data-path",
        dest="data_path",
        default=os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "data",
                "PHI-" + current_date + "-donor-data",
                "PHI-" + current_date + "-jsonData",
            )
        ),
        help="the output path where the data is stored"
    )

    parser.add_argument(
        "-w",
        "--weeks-of-data",
        dest="weeks_of_data",
        default=2,  # 52*10,  # go back the last 10 years as default
        help="enter the number of weeks of data you want to download"
    )

    parser.add_argument(
        "-ow",
        "--over-write",
        dest="overwrite_hours",
        default=24,
        help="if data was downloaded in the last <24> hours, skip download"
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
        "-s",
        "--save_file",
        dest="save_file",
        default="true",
        help="specify whether to save the downloaded donor data"
    )

    args = parser.parse_args()

    # the main function
    data, userid = get_data(
        save_data_path=args.data_path,
        weeks_of_data=args.weeks_of_data,
        overwrite_hours=args.overwrite_hours,
        donor_group=args.donor_group,
        userid=args.userid,
        auth=args.auth,
        email=args.email,
        password=args.password,
        save_file=args.save_file,
    )
