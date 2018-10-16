#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: download donors for each of the Tidepool donor groups
version: 0.0.3
created: 2018-02-21
author: Ed Nykaza
dependencies:
    * requires a list of qa accounts on production to be ignored
    * requires environmental variables: import environmentalVariables.py
license: BSD-2-Clause
"""


# %% load in required libraries
import pandas as pd
import datetime as dt
import numpy as np
import hashlib
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

parser.add_argument("--ignore-accounts",
                    dest="ignoreAccountsCsvFile",
                    default="PHI-2018-02-28-prod-accounts-to-be-ignored.csv",
                    help="a .csv file that contains a column heading " +
                    "'userID' and a list of userIDs to ignore")

args = parser.parse_args()


# %% Make sure the data directory exists
if not os.path.isdir(args.dataPath):
    os.makedirs(args.dataPath)


# %% define global variables
ignoreAccountsPath = os.path.join(args.dataPath, args.ignoreAccountsCsvFile)
donorGroupPath = os.path.join(args.dataPath, args.donorGroupsCsvFile)

donorGroups = pd.read_csv(donorGroupPath,
                          header=0,
                          names=["donorGroups"],
                          low_memory=False)

donorGroups = donorGroups.donorGroups

try:
    salt = os.environ["BIGDATA_SALT"]
except KeyError:
    sys.exit("Environment variable BIGDATA_SALT not found in .env file")

phiDateStamp = "PHI-" + args.dateStamp

donorMetadataColumns = ["userID", "name", "email",
                        "bDay", "dDay", "diagnosisType",
                        "targetDevices", "targetTimezone",
                        "termsAccepted", "hashID"]

alldonorMetadataList = pd.DataFrame(columns=donorMetadataColumns)

# create output folders
donorFolder = os.path.join(args.dataPath, phiDateStamp + "-donor-data")
if not os.path.exists(donorFolder):
    os.makedirs(donorFolder)

donorListFolder = os.path.join(donorFolder, phiDateStamp + "-donorLists")
if not os.path.exists(donorListFolder):
    os.makedirs(donorListFolder)

uniqueDonorPath = os.path.join(donorFolder,
                               phiDateStamp + "-uniqueDonorList.csv")


# %% define functions
def get_donor_info(email, password, donorMetadataColumns):
    donorMetaData = pd.DataFrame(columns=donorMetadataColumns)
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
                userID = usersData[i]["userid"]
                userName = usersData[i]["profile"]["fullName"]
                userEmail = usersData[i]["username"]

                try:
                    bDay = usersData[i]["profile"]["patient"]["birthday"]
                except Exception:
                    bDay = np.nan
                try:
                    dDay = usersData[i]["profile"]["patient"]["diagnosisDate"]
                except Exception:
                    dDay = np.nan
                try:
                    diagnosisType = usersData[i]["profile"]["patient"]["diagnosisType"]
                except Exception:
                    diagnosisType = np.nan
                try:
                    targetDevices = usersData[i]["profile"]["patient"]["targetDevices"]
                except Exception:
                    targetDevices = np.nan
                try:
                    targetTimezone = usersData[i]["profile"]["patient"]["targetTimezone"]
                except Exception:
                    targetTimezone = np.nan
                try:
                    termsAccepted = usersData[i]["termsAccepted"]
                except Exception:
                    termsAccepted = np.nan

                usr_string = userID + salt
                hash_user = hashlib.sha256(usr_string.encode())
                hashID = hash_user.hexdigest()
                donorMetaData = donorMetaData.append(
                        pd.DataFrame([[userID,
                                       userName,
                                       userEmail,
                                       bDay,
                                       dDay,
                                       diagnosisType,
                                       targetDevices,
                                       targetTimezone,
                                       termsAccepted,
                                       hashID]],
                                     columns=donorMetadataColumns),
                                     ignore_index=True)
        else:
            print(donorGroup, "ERROR", myResponse2.status_code)
            sys.exit("Error with" + donorGroup + ":" + str(myResponse2.status_code))
    else:
        print(donorGroup, "ERROR", myResponse.status_code)
        sys.exit("Error with" + donorGroup + ":" + str(myResponse.status_code))

    return donorMetaData


# %% loop through each donor group to get a list of donors, bdays, and ddays
for donorGroup in donorGroups:
    outputDonorList = os.path.join(donorListFolder, donorGroup + "-donors.csv")

    if donorGroup == "bigdata":
        donorGroup = ""

    # get environmental variables
    email, password = \
        environmentalVariables.get_environmental_variables(donorGroup)

    # load in bdays and ddays and append to all donor list
    donorMetadataList = get_donor_info(email, password, donorMetadataColumns)

    donorMetadataList.to_csv(outputDonorList)
    print("BIGDATA_" + donorGroup, "complete")
    donorMetadataList["donorGroup"] = donorGroup

    alldonorMetadataList = alldonorMetadataList.append(donorMetadataList,
                                                       ignore_index=True,
                                                       sort=False)

# %% save output
alldonorMetadataList.sort_values(by=['name', 'donorGroup'], inplace=True)
uniqueDonors = alldonorMetadataList.loc[~alldonorMetadataList["userID"].duplicated()]

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
      len(alldonorMetadataList),
      "records")

print("The total number of missing datapoints:",
      "\n",
      uniqueDonors[["bDay", "dDay"]].isnull().sum())

uniqueDonors.to_csv(uniqueDonorPath)
