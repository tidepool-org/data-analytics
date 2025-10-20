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

import get_donor_data.tidepool_api_bigdata as tpapi

envPath = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if envPath not in sys.path:
    sys.path.insert(0, envPath)
import environmentalVariables



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


def get_shared_metadata(
    donor_group="",
    userid_of_shared_user=np.nan,
):

    print("\tGetting user metadata..")
    auth = environmentalVariables.get_environmental_variables(donor_group)

    metadata_api_call = f"https://api.tidepool.org/metadata/{userid_of_shared_user}/profile"

    username, password = auth
    access_token = tpapi.retrieve_existing_token(username=username, password=password)

    headers = {
        "x-tidepool-session-token": access_token,
        "Content-Type": "application/json"
    }
    api_response = requests.get(metadata_api_call, headers=headers)
    df = pd.DataFrame(
        dtype=object,
        columns=[
            "diagnosisType",
            "diagnosisDate",
            "biologicalSex",
            "birthday",
            "targetTimezone",
            "targetDevices",
            "isOtherPerson",
            "about"
        ]
    )

    if(api_response.ok):
        user_profile = json.loads(api_response.content.decode())
        if "patient" in user_profile.keys():
            for k, d in zip(
                user_profile["patient"].keys(),
                user_profile["patient"].values()
            ):
                df.at[userid_of_shared_user, k] = d
    else:
        raise Exception(f"Error getting metadata API {str(api_response.status_code)}")

    tpapi.logout(username, password)

    df.index.rename("userid", inplace=True)

    print("\tFinished getting user metadata.")
    return df, userid_of_shared_user


# %% START OF CODE
def get_and_save_metadata(
    date_stamp=args.date_stamp,
    data_path=args.data_path,
    donor_group=args.donor_group,
    userid_of_shared_user=args.userid_of_shared_user,
    auth=args.auth,
    email=args.email,
    password=args.password
):
    # create output folders if they don't exist
    phi_date_stamp = "PHI-" + date_stamp
    donor_folder = os.path.join(data_path, phi_date_stamp + "-donor-data")

    metadata_path = os.path.join(
        donor_folder,
        phi_date_stamp + "-metadata"
    )
    make_folder_if_doesnt_exist(metadata_path)

    # get metadata
    meta_df, userid = get_shared_metadata(
        donor_group=donor_group,
        userid_of_shared_user=userid_of_shared_user,
        auth=auth,
        email=email,
        password=password
    )

    # save data
    meta_output_path = os.path.join(
        metadata_path,
        'PHI-' + userid + ".csv"
    )

    meta_df.to_csv(meta_output_path)


if __name__ == "__main__":
    get_and_save_metadata(
        date_stamp=args.date_stamp,
        data_path=args.data_path,
        donor_group=args.donor_group,
        userid_of_shared_user=args.userid_of_shared_user,
        auth=args.auth,
        email=args.email,
        password=args.password
    )
