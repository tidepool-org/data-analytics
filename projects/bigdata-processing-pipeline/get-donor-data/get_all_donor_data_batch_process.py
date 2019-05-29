# -*- coding: utf-8 -*-
"""accept_donors_and_pull_data.py
This is a wrapper script that accepts all bigdata donation project donors,
and then pulls of their datasets for further processing.
"""

# %% REQUIRED LIBRARIES
from accept_new_donors_and_get_donor_list import accept_and_get_list
from get_single_donor_metadata import get_and_save_metadata
from get_single_tidepool_dataset import get_and_save_dataset
import datetime as dt
import os
import argparse


# %% USER INPUTS (choices to be made in order to run the code)
codeDescription = "accepts new donors (shares) and grab their data"
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


# %%% REQUIRED LIBRARIES
final_donor_list = accept_and_get_list(args)

for userid, donor_group in zip(
    final_donor_list["userID"],
    final_donor_list["donorGroup"]
):
    get_and_save_metadata(
        date_stamp=args.date_stamp,
        data_path=args.data_path,
        donor_group=donor_group,
        userid_of_shared_user=userid
    )

    get_and_save_dataset(
        date_stamp=args.date_stamp,
        data_path=args.data_path,
        donor_group=donor_group,
        userid_of_shared_user=userid
    )
