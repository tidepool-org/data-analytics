#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: get donor list and pull json data
version: 0.0.1
created: 2018-02-21
author: Ed Nykaza
dependencies:
    * requires environmental variables, called by import settings
    * requires https://github.com/tidepool-org/command-line-data-tools
license: BSD-2-Clause
TODO:
* []
* []
* []
"""

# %% load in required libraries
import settings
import pandas as pd
import datetime as dt
import numpy as np
import glob
import hashlib
import os
import subprocess as sub
from pathlib import Path
import requests
from requests.auth import HTTPDigestAuth
import json


# %% user inputs (choices to be made to run code)
securePath = "/tidepoolSecure/data/"


# %% define global variables
donorGroups = ["", "BT1", "carbdm", "CDN", "CWD", "DHF", "DIATRIBE", "JDRF",
               "NSF", "SISTERS", "T1DX"]

dateStamp = dt.datetime.now().strftime("%Y") + "-" + \
    dt.datetime.now().strftime("%m") + "-" + \
    dt.datetime.now().strftime("%d")

allDonorsList = pd.DataFrame(columns=["userID", "name", "donorGroup"])
donorBandDdayList = pd.DataFrame(columns=["userID", "bDay", "dDay", "hashID"])

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

    return output, errors


# %% loop through each donor group to get a list of donors, bdays, and ddays
for donorGroup in donorGroups:
    outputDonorList = donorListFolder + donorGroup + "_donors.csv"

    # get environmental variables
    email, password = get_environmental_variables(donorGroup)

    # get the list of donors
    output, errors = get_donor_lists(email, password, outputDonorList)
    print(email, output, errors)

# %% code block 1
# TODO:
# * []
# * []
# * []

# %% code block 2
# TODO:
# * []
# * []
# * []

# %% code block N
# TODO:
# * []
# * []
# * []

# %% work-record-archive
# here are some common code elements
# specify where to start the code
startIndex = 0
endIndex = 1  # len(<dataset to loop through>)

#: save output (yes/no)
saveOutput = "no"

if saveOutput == "yes":
    print(saveOutput)
























