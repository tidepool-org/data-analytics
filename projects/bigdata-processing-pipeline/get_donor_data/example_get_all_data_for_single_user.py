# -*- coding: utf-8 -*-
"""example_get_all_data_for_single_user.py
This script shows examples for getting data for a single account,
and for accounts that are shared with another account, which is how
the bigdata donation project is managed.
"""

# %% REQUIRED LIBRARIES
from get_single_donor_metadata import get_shared_metadata
from get_single_tidepool_dataset import get_data


# %% EXAMPLES

# get metadata and data for a single user
# NOTE: you will be prompted to enter in your user credentials
metadata, _ = get_shared_metadata()
data, _ = get_data()

# get metadata and data for a donor that has shared with bigdata
# NOTE: functions assume you have an .env with bigdata account credentials
metadata, _ = get_shared_metadata(
    donor_group="bigdata",
    userid_of_shared_user="0d4524bc11"
)
data, _ = get_data(
    donor_group="bigdata",
    userid_of_shared_user="0d4524bc11",
    weeks_of_data=4
    )
