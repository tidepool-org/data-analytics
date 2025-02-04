# -*- coding: utf-8 -*-
"""accept-new-donors-and-get-donor-list.py
In the context of the big data donation
project, this code accepts new donors and returns a list of donors.

This code could also be modified rather easily to accept
new share invitations and return a list of userids that
are associated with the main account.
"""

# %% REQUIRED LIBRARIES
import pandas as pd
import datetime as dt
import os
import sys
import requests
import json
import argparse
envPath = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if envPath not in sys.path:
    sys.path.insert(0, envPath)
import environmentalVariables


# %% USER INPUTS (choices to be made in order to run the code)
codeDescription = "accepts new donors (shares) and return a list of userids"
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
    "-s",
    "--save-donor-list",
    dest="save_donor_list",
    default=True,
    help="specify if you want to save the donor list (True/False)"
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


def accept_invite_api(headers, userid):
    print("accepting new donors ...")
    nAccepted = 0
    api_call = "https://api.tidepool.org/confirm/invitations/" + userid
    api_response = requests.get(api_call, headers=headers)
    if(api_response.ok):

        usersData = json.loads(api_response.content.decode())

        for i in range(0, len(usersData)):
            shareKey = usersData[i]["key"]
            shareID = usersData[i]["creatorId"]
            payload = {
                "key": shareKey
            }

            api_call2 = "https://api.tidepool.org/confirm/accept/invite/" + \
                userid + "/" + shareID

            api_response2 = requests.put(
                api_call2,
                headers=headers,
                json=payload
            )

            if(api_response2.ok):
                nAccepted = nAccepted + 1
            else:
                sys.exit(
                    "Error with accepting invites",
                    api_response2.status_code
                )

    elif api_response.status_code == 404:
        # this is the case where there are no new invitations
        print("very likely that no new invitations exist")
    else:
        sys.exit(
            "Error with getting list of invitations",
            api_response.status_code
        )

    return nAccepted


def get_donor_list_api(headers, userid):
    print("getting donor list ...")
    api_call = "https://api.tidepool.org/access/groups/" + userid
    api_response = requests.get(api_call, headers=headers)
    if(api_response.ok):
        donors_list = json.loads(api_response.content.decode())
    else:
        sys.exit(
            "Error with donor list api",
            api_response.status_code
        )
    df = pd.DataFrame(list(donors_list.keys()), columns=["userID"])

    return df


def accept_new_donors_and_get_donor_list(auth):
    # login
    headers, userid = login_api(auth)
    # accept invitations to the master donor account
    nAccepted = accept_invite_api(headers, userid)
    # get a list of donors associated with the master account
    df = get_donor_list_api(headers, userid)
    # logout
    logout_api(auth)

    return nAccepted, df


# %% START OF CODE
def accept_and_get_list(args):
    # create output folders
    date_stamp = args.date_stamp  # dt.datetime.now().strftime("%Y-%m-%d")
    phi_date_stamp = "PHI-" + date_stamp
    donor_folder = os.path.join(args.data_path, phi_date_stamp + "-donor-data")
    make_folder_if_doesnt_exist(donor_folder)

    uniqueDonorList_path = os.path.join(
        donor_folder,
        phi_date_stamp + "-uniqueDonorList.csv"
    )

    # define the donor groups
    donor_groups = [
        "bigdata", "AADE", "BT1", "carbdm", "CDN",
        "CWD", "DHF", "DIATRIBE", "diabetessisters",
        "DYF", "JDRF", "NSF", "T1DX",
    ]

    all_donors_df = pd.DataFrame(columns=["userID", "donorGroup"])

    # accounts to ignore (QA testing)
    accounts_to_ignore = [
        'f597f21dcd', '0ef51a0121', '38c3795fcb', '69c99b51f6', '84c2cdd947',
        '9cdebdc316', '9daaf4d4c1', 'bdf4724bed', 'c7415b5097', 'dccc3baf63',
        'ee145393b0', '00cd0ffada', '122a0bf6c5', '898c3d8056', '9e4f3fbc2a',
        '1ebe2a2790', '230650bb9c', '3f8fdabcd7', '636aad0f58', '70df39aa43',
        '92a3c903fe', '3043996405', '0239c1cfb2', '03852a5acc', '03b1953135',
        '0ca5e75e4a', '0d8bdb05eb', '19123d4d6a', '19c25d34b5', '1f6866bebc',
        '1f851c13a5', '275ffa345f', '275ffa345f', '3949134b4a', '410865ba56',
        '57e2b2ed3d', '59bd6891e9', '5acf17a80a', '627d0f4bf1', '65247f8257',
        '6e5287d4c4', '6fc3a4ad44', '78ea6c3cad', '7d8a80e8ce', '8265248ea3',
        '8a411facd2', '98f81fae18', '9d601a08a3', 'aa9fbc4ef5', 'aaac56022a',
        'adc00844c3', 'aea4b3d8ea', 'bc5ee641a3', 'c8328622d0', 'cfef0b91ac',
        'df54366b1c', 'e67aa71493', 'f2103a44d5', 'dccc3baf63'
    ]

    for donor_group in donor_groups:
        if donor_group == "bigdata":
            dg = ""
        else:
            dg = donor_group

        nNewDonors, donors_df = accept_new_donors_and_get_donor_list(
            environmentalVariables.get_environmental_variables(dg)
        )

        donors_df["donorGroup"] = donor_group
        print(donor_group, "complete, there are %d new donors\n" % nNewDonors)
        all_donors_df = pd.concat([all_donors_df, donors_df])

    all_donors_df.sort_values(by=['userID', 'donorGroup'], inplace=True)
    unique_donors = all_donors_df.loc[~all_donors_df["userID"].duplicated()]
    total_donors = len(set(unique_donors["userID"]) - set(accounts_to_ignore))

    final_donor_list = pd.DataFrame(
        list(set(unique_donors["userID"]) - set(accounts_to_ignore)),
        columns=["userID"]
    )

    final_donor_list = pd.merge(
        final_donor_list,
        unique_donors,
        how="left",
        on="userID"
    )

    # polish up the final donor list
    final_donor_list.sort_values(by="donorGroup", inplace=True)
    final_donor_list.reset_index(drop=True, inplace=True)

    if args.save_donor_list:
        print("saving donor list ...\n")
        final_donor_list.to_csv(uniqueDonorList_path)
    else:
        print("donor list is NOT being saved ...\n")

    print("There are %d total donors," % total_donors)
    print("after removing donors that donated to more than 1 group,")
    print("and after removing QA testing accounts.")

    return final_donor_list


if __name__ == "__main__":
    final_donor_list = accept_and_get_list(args)
