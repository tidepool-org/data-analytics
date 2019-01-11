#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: get users settings and events
version: 0.0.1
created: 2019-01-11
author: Ed Nykaza
dependencies:
    *
license: BSD-2-Clause
"""


# %% REQUIRED LIBRARIES
import pandas as pd
import datetime as dt
import numpy as np
import os
import sys
import shutil
import glob
import argparse
import hashlib
import ast
import time


# %% USER INPUTS (ADD THIS IN LATER)
#codeDescription = "Get user's settings and events"
#parser = argparse.ArgumentParser(description=codeDescription)


# %% LOAD IN ONE FILE, BUT EVENTUALLY THIS WILL LOOOP THROUGH ALL USER'S


# %% ID & HASHID


# %% AGE & YLW


# %% UPLOAD DATE


# %% TIME (UTC, TIMEZONE, AND EVENTUALLY LOCAL TIME)


# %% PUMP AND CGM DEVICE ()


# %% ISF


# %% CIR


# %% INSULIN ACTIVITY DURATION


# %% MAX BASAL RATE


# %% MAX BOLUS AMOUNT


# %% CORRECTION TARGET


# %% BASAL RATES (TIME, VALUE, DURATION, TYPE (SCHEDULED, TEMP, SUSPEND))


# %% LOOP DATA (BINARY T/F)


# %% BOLUS EVENTS (CORRECTION, AND MEAL INCLUING: CARBS, EXTENDED, DUAL)


# %% CGM DATA


# %% NUMBER OF DAYS OF PUMP AND CGM DATA, OVERALL AND PER EACH AGE & YLW


# %% STATS PER EACH TYPE, OVERALL AND PER EACH AGE & YLW (MIN, PERCENTILES, MAX, MEAN, SD, IQR, COV)


# %% SAVE RESULTS


# %% MAKE THIS A FUNCTION SO THAT IT CAN BE RUN PER EACH INDIVIDUAL


# %% V2 DATA TO GRAB
# ALERT SETTINGS
# ESTIMATED LOCAL TIME
# GLYCEMIC OUTCOMES
# DO NOT ROUND DATA
# INFUSION SITE CHANGES
# CGM CALIBRATIONS
