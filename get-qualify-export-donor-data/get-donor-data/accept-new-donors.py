#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: accept new donors
version: 0.0.1
created: 2018-09-05
author: Ed Nykaza
dependencies:
    * requires environmental variables: import environmentalVariables.py
license: BSD-2-Clause
"""


# %% load in required libraries
import pandas as pd
import datetime as dt
import numpy as np
import os
import sys
import requests
import json
import argparse
envPath = os.path.abspath(os.path.join(__file__, "..", "..", "..",
                                       "get-qualify-export-donor-data"))
if envPath not in sys.path:
    sys.path.insert(0, envPath)
import environmentalVariables


# %% user inputs (choices to be made in order to run the code)
codeDescription = "Download a list of donors for each of the Tidepool" + \
                  "accounts defined in .env"

parser = argparse.ArgumentParser(description=codeDescription)

parser.add_argument("-d",
                    "--date-stamp",
                    dest="dateStamp",
                    default=dt.datetime.now().strftime("%Y-%m-%d"),
                    help="date, in '%Y-%m-%d' format, of the date when " +
                    "donors were accepted")

parser.add_argument("-i",
                    "--input-donor-groups",
                    dest="donorGroupsCsvFile",
                    default="2018-09-04-donor-groups.csv",
                    help="a .csv file that contains a column heading " +
                    "'donorGroups' and a list of donor groups")

parser.add_argument("-o",
                    "--output-data-path",
                    dest="dataPath",
                    default=os.path.abspath(os.path.join(__file__, "..", "..", "data")),
                    help="the output path where the data is stored")

args = parser.parse_args()


# %% Make sure the data directory exists
if not os.path.isdir(args.dataPath):
    sys.exit("{0} is not a directory".format(args.dataPath))


# %% define global variables
donorGroupPath = os.path.join(args.dataPath, args.donorGroupsCsvFile)

donorGroups = pd.read_csv(donorGroupPath,
                          header=0,
                          names=["donorGroups"],
                          low_memory=False)

donorGroups[args.dateStamp] = np.nan

# create output folders
newDonorFolder = os.path.join(args.dataPath, "newDonors", "")
if not os.path.exists(newDonorFolder):
    os.makedirs(newDonorFolder)


# %% define functions
def get_secrets(donorGroup):
    if donorGroup == "bigdata":
        donorGroup = ""
    email, password = \
        environmentalVariables.get_environmental_variables(donorGroup)

    return email, password


def accept_new_donor(email, password):
    nAccepted = 0
    url1 = "https://api.tidepool.org/auth/login"
    myResponse = requests.post(url1, auth=(email, password))

    if(myResponse.ok):
        xtoken = myResponse.headers["x-tidepool-session-token"]
        userid = json.loads(myResponse.content.decode())["userid"]
        url2 = "https://api.tidepool.org/confirm/invitations/" + userid
        headers = {
            "x-tidepool-session-token": xtoken,
            "Content-Type": "application/json"
        }

        myResponse2 = requests.get(url2, headers=headers)
        if(myResponse2.ok):

            usersData = json.loads(myResponse2.content.decode())

            for i in range(0, len(usersData)):
                shareKey = usersData[i]["key"]
                shareID = usersData[i]["creatorId"]
                payload = {
                    "key": shareKey
                }

                url3 = "https://api.tidepool.org/confirm/accept/invite/" + \
                    userid + "/" + shareID

                myResponse3 = requests.put(url3, headers=headers, json=payload)

                if(myResponse3.ok):
                    nAccepted = nAccepted + 1
                else:
                    print(email, "ERROR", myResponse3.status_code)
                    sys.exit("Error with " + email + ":" + str(myResponse3.status_code))
        elif myResponse2.status_code == 404:
            # this is the case where there are no new invitations
            print("very likely that no new invitations exist")
        else:
            print(email, "ERROR", myResponse2.status_code)
            sys.exit("Error with " + email + ":" + str(myResponse2.status_code))
    else:
        print(email, "ERROR", myResponse.status_code)
        sys.exit("Error with " + email + ":" + str(myResponse.status_code))

    return nAccepted


# %% loop through each donor group to get a list of donors, bdays, and ddays
for dgIndex in range(0, len(donorGroups)):
    donorGroup = donorGroups.loc[dgIndex, "donorGroups"]

    # get environmental variables
    email, password = get_secrets(donorGroup)

    # load in bdays and ddays and append to all donor list
    nNewDonors = accept_new_donor(email, password)
    donorGroups.loc[dgIndex, args.dateStamp] = nNewDonors

    print("BIGDATA_" + donorGroup, "complete, N =", nNewDonors)


# %% save output
donorGroups.to_csv(os.path.join(newDonorFolder, args.dateStamp + "-donorCounts.csv"),
                   index=False)
