#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: get donor list and pull json data
version: 0.0.1
created: 2018-02-21
author: Ed Nykaza
dependencies:
    * requires environmental variables: import environmentalVariables.py
    * requires https://github.com/tidepool-org/command-line-data-tools
license: BSD-2-Clause
TODO:
* [] need to add in check for donors that are on the QA production list
* []
* []
"""

# %% load in required libraries
import environmentalVariables
import pandas as pd
import datetime as dt
import numpy as np
import hashlib
import os
import sys
import subprocess as sub
#from pathlib import Path
import requests
from requests.auth import HTTPDigestAuth
import json


# %% user inputs (choices to be made to run code)
securePath = "/tidepoolSecure/data/"


# %% define global variables
donorGroups = ["", "BT1", "carbdm", "CDN", "CWD", "DHF", "DIATRIBE",
               "diabetessisters", "DYF", "JDRF", "NSF", "T1DX"]


salt = os.environ["BIGDATA_SALT"]

dateStamp = dt.datetime.now().strftime("%Y") + "-" + \
    dt.datetime.now().strftime("%m") + "-" + \
    dt.datetime.now().strftime("%d")

allDonorsList = pd.DataFrame(columns=["userID", "name", "donorGroup"])
donorBandDdayListColumns = ["userID", "bDay", "dDay", "hashID", "donorGroup"]
allDonorBandDdayList = pd.DataFrame(columns=donorBandDdayListColumns)

# create output folders
donorListFolder = securePath + dateStamp + "_donorLists/"
if not os.path.exists(donorListFolder):
    os.makedirs(donorListFolder)

donorJsonDataFolder = securePath + dateStamp + "_donorJsonData/"
if not os.path.exists(donorJsonDataFolder):
    os.makedirs(donorJsonDataFolder)


# %% define functions
def get_environmental_variables(donorGroup):
    envEmailVariableName = "BIGDATA_" + donorGroup + "_EMAIL"
    emailAddress = os.environ[envEmailVariableName]

    envPasswordVariableName = "BIGDATA_" + donorGroup + "_PASSWORD"
    pswd = os.environ[envPasswordVariableName]

    return emailAddress, pswd


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

        donorList["donorGroup"] = donorGroup

    return donorList


def get_bdays_and_ddays(email, password, donorGroup, donorBandDdayListColumns):

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
                                       hashID,
                                       donorGroup]],
                                     columns=donorBandDdayListColumns),
                        ignore_index=True)
        else:
            print(donorGroup, myResponse2.status_code)
    else:
        print(donorGroup, myResponse.status_code)

    return tempBandDdayList


# %% loop through each donor group to get a list of donors, bdays, and ddays
for donorGroup in donorGroups:
    outputDonorList = donorListFolder + donorGroup + "_donors.csv"

    # get environmental variables
    email, password = get_environmental_variables(donorGroup)

    # get the list of donors
    get_donor_lists(email, password, outputDonorList)

    # load in the donor list
    donorList = load_donors(outputDonorList, donorGroup)
    allDonorsList = allDonorsList.append(donorList, ignore_index=True)

    # load in bdays and ddays
    donorBandDdayList = get_bdays_and_ddays(email,
                                            password,
                                            donorGroup,
                                            donorBandDdayListColumns)

    allDonorBandDdayList = allDonorBandDdayList.append(donorBandDdayList,
                                                       ignore_index=True)

    print(donorGroup, "complete")

# %% save output

uniqueDonors = allDonorBandDdayList.loc[
        ~allDonorBandDdayList["userID"].duplicated()]
uniqueDonors = uniqueDonors.reset_index(drop=True)
print("There are",
      len(uniqueDonors),
      "unique donors, of the",
      len(allDonorsList),
      "records")
print("The total number of missing datapoints:",
      "\n",
      uniqueDonors.isnull().sum())

uniqueDonors.to_csv(securePath + dateStamp + "_uniqueDonorList.csv")

























