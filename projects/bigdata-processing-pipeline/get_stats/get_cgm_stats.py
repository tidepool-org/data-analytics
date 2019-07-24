#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
calculate cgm statsistics for a single tidepool (donor) dataset
'''


# %% REQUIRED LIBRARIES
import os
import sys
# TODO: figure out how to get rid of these path dependcies
get_donor_data_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
if get_donor_data_path not in sys.path:
    sys.path.insert(0, get_donor_data_path)
from get_donor_data.get_single_donor_metadata import get_shared_metadata
from get_donor_data.get_single_tidepool_dataset import get_data


# %% GET DATA FROM API
'''
get metadata and data for a donor that has shared with bigdata
NOTE: functions assume you have an .env with bigdata account credentials
'''

userid = "0d4524bc11"
donor_group = "bigdata"

metadata, _ = get_shared_metadata(
    donor_group=donor_group,
    userid_of_shared_user=userid
)
data, _ = get_data(
    donor_group=donor_group,
    userid=userid,
    weeks_of_data=52
    )


