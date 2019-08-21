# -*- coding: utf-8 -*-
"""accept_donors_and_pull_data.py
This is a wrapper script that gets distributions and stats for all donors,
NOTE: this needs to be refactored because it is currently set up to run
on json files that are in a snowflake path

"""

# %% REQUIRED LIBRARIES
import pandas as pd
import os
import glob
import argparse


# %% USER INPUTS (choices to be made in order to run the code)
codeDescription = "get distribution and stats for all donor's json data"
parser = argparse.ArgumentParser(description=codeDescription)

parser.add_argument(
    "-d",
    "--date-stamp",
    dest="date_stamp",
    default="2019-07-17",
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

args = parser.parse_args()


# %% COMBINE AND SAVE ALL DONOR METADATA
print("combining all metadata")
phi_date_stamp = "PHI-" + args.date_stamp
donor_folder = os.path.join(args.data_path, phi_date_stamp + "-donor-data")

metadata_path = os.path.join(
    args.data_path,
    phi_date_stamp + "-donor-data",
    phi_date_stamp + "-cgm-metadata"
)

all_metadata_files = glob.glob(os.path.join(metadata_path, "*.csv.gz"))
all_metadata = pd.DataFrame()
for f in all_metadata_files:
    temp_meta = pd.read_csv(f, low_memory=False)
    all_metadata = pd.concat(
        [all_metadata, temp_meta],
        ignore_index=True,
        sort=False
    )

all_metadata.to_csv(
    os.path.join(donor_folder, phi_date_stamp + "-cgm-metadata.csv.gz")
)
print("saving metadata...code complete")


# %% COMBINE AND SAVE ALL DISTRIBUTION DATA
print("combining all distribution data")

metadata_path = os.path.join(
    args.data_path,
    phi_date_stamp + "-donor-data",
    phi_date_stamp + "-cgm-distributions"
)

all_metadata_files = glob.glob(os.path.join(metadata_path, "*.csv.gz"))
distribution_metadata = pd.DataFrame()
for f in all_metadata_files:
    temp_meta = pd.read_csv(f, index_col=[0], low_memory=False)
    distribution_metadata = pd.concat(
        [distribution_metadata, temp_meta],
        ignore_index=True,
        sort=False
    )

distribution_metadata.to_csv(
    os.path.join(
        donor_folder, phi_date_stamp + "-all-cgm-distributions.csv.gz"
    )
)
print("saving all-dataset-info-metadata...code complete")
