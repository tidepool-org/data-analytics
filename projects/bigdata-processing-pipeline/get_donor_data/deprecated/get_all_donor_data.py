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
import requests
import json
import subprocess as sub
import argparse
envPath = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if envPath not in sys.path:
    sys.path.insert(0, envPath)
import environmentalVariables


# %% USER INPUTS (choices to be made in order to run the code)
codeDescription = "get all donor data"
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
    "-w",
    "--overwrite",
    dest="overwrite",
    default=False,
    help="specify if you only want to save metadata, default is False"
)

parser.add_argument(
    "-m",
    "--metadata-only",
    dest="metadata_only",
    default=False,
    help="specify if you only want to save metadata, default is False"
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


def login_api(auth):
    api_call = "https://api.tidepool.org/auth/login"
    api_response = requests.post(api_call, auth=auth)
    if(api_response.ok):
        xtoken = api_response.headers["x-tidepool-session-token"]
        userid = json.loads(api_response.content.decode())["userid"]
        headers = {
            "x-tidepool-session-token": xtoken,
            "Content-Type": "application/json"
        }

    else:
        sys.exit("Error with " + auth[0] + ":" + str(api_response.status_code))

    print("logging into", auth[0], "...")

    return headers, userid


def logout_api(auth):
    api_call = "https://api.tidepool.org/auth/logout"
    api_response = requests.post(api_call, auth=auth)

    if(api_response.ok):
        print("successfully logged out of", auth[0])

    else:
        sys.exit(
            "Error with logging out for " +
            auth[0] + ":" + str(api_response.status_code)
        )

    return


def get_metadata_api(userid, headers):
    print("get donor metadata for %s ..." % userid)
    api_call = "https://api.tidepool.org/metadata/%s/profile" % userid
    api_response = requests.get(api_call, headers=headers)
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
                df.at[userid, k] = d
    else:
        sys.exit(
            "Error getting metadata API " +
            str(api_response.status_code)
        )
    return df


def get_all_data_api(userid, years_of_data=10):
    print("downloading data ...")
    # download user data
    df = pd.DataFrame()
    endDate = pd.datetime.now()

    for years in range(0, years_of_data + 1):
        startDate = endDate - pd.Timedelta(365, unit="d")

        api_call = (
            "https://api.tidepool.org/data/" + userid + "?" +
            "endDate=" + endDate.strftime("%Y-%m-%d") + "T23:59:59.000Z" + "&" +
            "startDate=" + startDate.strftime("%Y-%m-%d") + "T00:00:00.000Z" + "&" +
            "dexcom=true" + "&" +
            "medtronic=true" + "&" +
            "carelink=true"
        )

        api_response = requests.get(api_call, headers=headers)
        if(api_response.ok):
            json_data = json.loads(api_response.content.decode())
            year_df = pd.DataFrame(json_data)
            df = pd.concat(
                [df, year_df],
                ignore_index=True,
                sort=False
            )

        else:
            sys.exit(
                "ERROR in getting data for year ",
                years,
                api_response.status_code
            )

        endDate = startDate - pd.Timedelta(1, unit="d")

    return df


def run_accept_donors(args):
    print("accepting new donors and getting donor list ...")
    accept_new_donor_path = os.path.join(
        ".", "accept_new_donors_and_get_donor_list.py"
    )
    p = sub.Popen(
        [
             "python", accept_new_donor_path,
             "-d", args.date_stamp,
             "-o", args.data_path
         ],
        stdout=sub.PIPE,
        stderr=sub.PIPE
    )

    output, errors = p.communicate()
    output = output.decode("utf-8")
    errors = errors.decode("utf-8")

    if errors == '':
        print(output)
    else:
        sys.exit(errors)

    return output, errors


# %% START OF CODE
# first accept new donors and generate a list of donors
accept_output, accept_errors = run_accept_donors(args)

# create output folders
date_stamp = args.date_stamp  # dt.datetime.now().strftime("%Y-%m-%d")
phi_date_stamp = "PHI-" + date_stamp
donor_folder = os.path.join(args.data_path, phi_date_stamp + "-donor-data")
make_folder_if_doesnt_exist(donor_folder)

uniqueDonorList_path = os.path.join(
    donor_folder,
    phi_date_stamp + "-uniqueDonorList.csv"
)

metaDonorPath = os.path.join(
    donor_folder,
    phi_date_stamp + "-uniqueDonorList-with-metaData.csv"
)

# define the donor groups
donor_groups = [
    "bigdata", "AADE", "BT1", "carbdm", "CDN",
    "CWD", "DHF", "DIATRIBE", "diabetessisters",
    "DYF", "JDRF", "NSF", "T1DX",
]

csv_path = os.path.join(
    donor_folder,
    phi_date_stamp + "-donorCsvData"
)

temp_meta_path = os.path.join(
    donor_folder,
    phi_date_stamp + "-tempMeta"
)

make_folder_if_doesnt_exist([csv_path, temp_meta_path])

temp_meta_output_path = os.path.join(
    temp_meta_path,
    "temp-meta-" + dt.datetime.now().strftime("%Y-%m-%d-%H-%M-%p") + ".csv"
)

donor_list = pd.read_csv(
    uniqueDonorList_path,
    index_col=0,
    low_memory=False
)

meta_df = pd.DataFrame(
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

# % loop through each user and get data
for donor_group in donor_list["donorGroup"].unique():
    if donor_group == "bigdata":
        dg = ""
    else:
        dg = donor_group

    headers, userid = login_api(
        environmentalVariables.get_environmental_variables(dg)
    )

    userids = donor_list.loc[donor_list["donorGroup"] == donor_group, "userID"]
    for userid in userids:
        temp_df = get_metadata_api(userid, headers)

        csv_output_path = os.path.join(
            csv_path,
            "PHI-" + userid + ".csv"
        )

        skip_if_no_overwrite_and_file_exists = (
           (not args.overwrite) &
           (os.path.exists(csv_output_path))
        )

        if not args.metadata_only:
            if not skip_if_no_overwrite_and_file_exists:
                data = get_all_data_api(userid)
                data_rows = len(data)
                if data_rows > 0:
                    # save the donr data
                    data.to_csv(csv_output_path)

                print("done with %s, data has %s rows\n" % (userid, data_rows))
            else:
                print("skipping %s, b/c file already exists" % userid)
        else:
            data_rows = np.nan

        temp_df["nRows"] = data_rows
        meta_df = pd.concat([meta_df, temp_df], sort=False)
        meta_df.to_csv(temp_meta_output_path)

    logout_api(
        environmentalVariables.get_environmental_variables(dg)
    )

    print("done with donor group: %s \n" % donor_group)

# add the meta data to the donor data
meta_df.reset_index(inplace=True)
meta_df.rename(columns={"index": "userID"}, inplace=True)
donor_list = pd.merge(
    donor_list,
    meta_df,
    how="left",
    on="userID"
)

# save the results
donor_list.to_csv(metaDonorPath)
