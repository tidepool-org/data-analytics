#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: get the most recent donor list
version: 0.0.1
created: 2018-02-21
author: Ed Nykaza
dependencies:
    * requires that donors are accepted (currently a manual process)
    * requires a list of qa accounts on production to be ignored
    * requires environmental variables: import environmentalVariables.py
    * requires https://github.com/tidepool-org/command-line-data-tools
license: BSD-2-Clause
TODO:
* [] waiting for QA to cross reference donor accounts with testing accounts,
once they do, then the ignoreAccounts file needs to be updated
* [] once the process of accepting new donors is automated, the use of the
dateStamp will make more sense. As it is being used now, it is possible that
the dateStamp does NOT reflect all of the recent donors.
"""

# %% load in required libraries
import pandas as pd
import datetime as dt
import numpy as np
import hashlib
import os
import sys
import subprocess as sub
import requests
import json
import argparse

parser = argparse.ArgumentParser(description='Download a list of donors for each of the Tidepool accounts defined in .env')
parser.add_argument('--data-path', dest='dataPath', default='./data',
                    help='the path where the data is stored')
args = parser.parse_args()

# Make sure the data directory exists
if not os.path.isdir(args.dataPath):
    sys.exit('{0} is not a directory'.format(args.dataPath))

# Only read the .env file after parsing command line args
import environmentalVariables

# %% user inputs (choices to be made to run code)
ignoreAccountsPath = os.path.join(args.dataPath,
    "PHI-2018-02-28-prod-accounts-to-be-ignored.csv")

donorGroups = ["bigdata", "BT1", "carbdm", "CDN", "CWD", "DHF", "DIATRIBE",
               "diabetessisters", "DYF", "JDRF", "NSF", "T1DX"]


# %% define global variables
try:
    salt = os.environ["BIGDATA_SALT"]
except KeyError:
    sys.exit('Environment variable BIGDATA_SALT not found in .env file')

dateStamp = dt.datetime.now().strftime("%Y") + "-" + \
    dt.datetime.now().strftime("%m") + "-" + \
    dt.datetime.now().strftime("%d")

phiDateStamp = "PHI-" + dateStamp

donorBandDdayListColumns = ["userID", "bDay", "dDay", "hashID"]

allDonorBandDdayList = pd.DataFrame(columns=donorBandDdayListColumns)

# create output folders
donorFolder = os.path.join(args.dataPath, phiDateStamp + "-donor-data")
if not os.path.exists(donorFolder):
    os.makedirs(donorFolder)

donorListFolder = os.path.join(donorFolder, phiDateStamp + "-donorLists")
if not os.path.exists(donorListFolder):
    os.makedirs(donorListFolder)

uniqueDonorPath = os.path.join(donorFolder, phiDateStamp + "-uniqueDonorList.csv")


# %% define functions
def get_donor_lists(email, password, outputDonorList):
    p = sub.Popen(["getusers", email,
                   "-p", password, "-o",
                   outputDonorList, "-v"], stdout=sub.PIPE, stderr=sub.PIPE)

    output, errors = p.communicate()
    output = output.decode("utf-8")
    errors = errors.decode("utf-8")

    if output.startswith("Successful login.\nSuccessful") is False:
        sys.exit("ERROR with" + email +
                 " ouput: " + output +
                 " errorMessage: " + errors)

    return


def load_donors(outputDonorList, donorGroup):
    donorList = []
    if os.stat(outputDonorList).st_size > 0:
        donorList = pd.read_csv(outputDonorList,
                                header=None,
                                usecols=[0, 1],
                                names=["userID", "name"],
                                low_memory=False)
        if donorGroup == "":
            donorGroup = "bigdata"
        donorList[donorGroup] = True
        donorList["donorGroup"] = donorGroup

    return donorList


def get_bdays_and_ddays(email, password, donorBandDdayListColumns):

    tempBandDdayList = pd.DataFrame(columns=donorBandDdayListColumns)
    url1 = "https://api.tidepool.org/auth/login"
    myResponse = requests.post(url1, auth=(email, password))

    if(myResponse.ok):
        xtoken = myResponse.headers["x-tidepool-session-token"]
        userid = json.loads(myResponse.content.decode())["userid"]
        url2 = "https://api.tidepool.org/metadata/users/" + userid + "/users"
        headers = {
            "x-tidepool-session-token": xtoken,
            "Content-Type": "application/json"
        }

        myResponse2 = requests.get(url2, headers=headers)
        if(myResponse2.ok):

            usersData = json.loads(myResponse2.content.decode())

            for i in range(0, len(usersData)):
                try:
                    bDay = usersData[i]["profile"]["patient"]["birthday"]
                except Exception:
                    bDay = np.nan
                try:
                    dDay = usersData[i]["profile"]["patient"]["diagnosisDate"]
                except Exception:
                    dDay = np.nan
                userID = usersData[i]["userid"]
                usr_string = userID + salt
                hash_user = hashlib.sha256(usr_string.encode())
                hashID = hash_user.hexdigest()
                tempBandDdayList = tempBandDdayList.append(
                        pd.DataFrame([[userID,
                                       bDay,
                                       dDay,
                                       hashID]],
                                     columns=donorBandDdayListColumns),
                        ignore_index=True)
        else:
            print(donorGroup, "ERROR", myResponse2.status_code)
    else:
        print(donorGroup, "ERROR", myResponse.status_code)

    return tempBandDdayList


# %% loop through each donor group to get a list of donors, bdays, and ddays
for donorGroup in donorGroups:
    outputDonorList = os.path.join(donorListFolder, donorGroup + "-donors.csv")

    if donorGroup == "bigdata":
        donorGroup = ""

    # get environmental variables
    email, password = \
        environmentalVariables.get_environmental_variables(donorGroup)

    # get the list of donors
    get_donor_lists(email, password, outputDonorList)

    # load in the donor list
    donorList = load_donors(outputDonorList, donorGroup)

    # load in bdays and ddays and append to all donor list
    donorBandDdayList = get_bdays_and_ddays(email,
                                            password,
                                            donorBandDdayListColumns)

    donorBandDdayList = pd.merge(donorBandDdayList,
                                 donorList,
                                 how="left",
                                 on="userID")

    allDonorBandDdayList = allDonorBandDdayList.append(donorBandDdayList,
                                                       ignore_index=True)

    print("BIGDATA_" + donorGroup, "complete")


# %% save output

uniqueDonors = allDonorBandDdayList.loc[
        ~allDonorBandDdayList["userID"].duplicated(),
        donorBandDdayListColumns + ["name", "donorGroup"]]

# add donor groups to unique donors
donorCounts = allDonorBandDdayList.groupby("userID").count()
donorCounts = donorCounts[donorGroups]
donorCounts["userID"] = donorCounts.index

uniqueDonors = pd.merge(uniqueDonors,
                        donorCounts,
                        how="left",
                        on="userID")

# cross reference the QA users here and DROP them
ignoreAccounts = pd.read_csv(ignoreAccountsPath, low_memory=False)
uniqueIgnoreAccounts = \
    ignoreAccounts[ignoreAccounts.Userid.notnull()].Userid.unique()

for ignoreAccount in uniqueIgnoreAccounts:
    uniqueDonors = uniqueDonors[uniqueDonors.userID != ignoreAccount]

uniqueDonors = uniqueDonors.reset_index(drop=True)
uniqueDonors.index.name = "dIndex"

print("There are",
      len(uniqueDonors),
      "unique donors, of the",
      len(allDonorBandDdayList),
      "records")

print("The total number of missing datapoints:",
      "\n",
      uniqueDonors[["bDay", "dDay"]].isnull().sum())

uniqueDonors.to_csv(uniqueDonorPath)
