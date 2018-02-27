#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: load environment variables
version: 0.0.1
created: 2018-02-21
author: Ed Nykaza
dependencies:
    * .env file in same folder as this script (Tidepool see bigdata 1PWD)
license: BSD-2-Clause
"""

# %% load in required libraries
import os
from os.path import join, dirname
from dotenv import load_dotenv

# %% load environmental variables
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

# %% define functions


def get_environmental_variables(donorGroup):
    envEmailVariableName = "BIGDATA_" + donorGroup + "_EMAIL"
    emailAddress = os.environ[envEmailVariableName]

    envPasswordVariableName = "BIGDATA_" + donorGroup + "_PASSWORD"
    pswd = os.environ[envPasswordVariableName]

    return emailAddress, pswd
