# -*- coding: utf-8 -*-
"""accept_donors_and_pull_data.py
This is a wrapper script that gets distributions and stats for all donors,
NOTE: this needs to be refactored because it is currently set up to run
on json files that are in a snowflake path

"""

# %% REQUIRED LIBRARIES
import pandas as pd
import numpy as np
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

parser.add_argument(
    "-c",
    "--chunk-size",
    dest="chunk_size",
    default=50,
    help="the output path where the data is stored"
)

args = parser.parse_args()


# %% COMBINE AND SAVE ALL DISTRIBUTION DATA

phi_date_stamp = "PHI-" + args.date_stamp
donor_folder = os.path.join(args.data_path, phi_date_stamp + "-donor-data")

metadata_path = os.path.join(
    args.data_path,
    phi_date_stamp + "-donor-data",
    phi_date_stamp + "-cgm-distributions"
)

all_metadata_files = glob.glob(os.path.join(metadata_path, "*.csv.gz"))
print("combining {} distribution data files".format(len(all_metadata_files)))
chunks = np.arange(0, len(all_metadata_files), int(args.chunk_size))
chunks = np.append(chunks, len(all_metadata_files))
for chunk_start, chunk_end in zip(chunks[0:-1], chunks[1:]):
    print("starting chunk {}-{}".format(str(chunk_start), str(chunk_end)))
    distribution_metadata = pd.DataFrame()
    for c_idx in np.arange(chunk_start, chunk_end):
        temp_meta = pd.read_csv(
            all_metadata_files[c_idx],
            index_col=[0],
            low_memory=False
        )
        distribution_metadata = pd.concat(
            [distribution_metadata, temp_meta],
            ignore_index=True,
            sort=False
        )
    # save chunk
    print("saving chunk {}-{}".format(str(chunk_start), str(chunk_end)))
    distribution_metadata.to_csv(
        os.path.join(
            donor_folder,
            phi_date_stamp + "-cgm-distributions-{}-{}.csv.gz".format(
                str(chunk_start),
                str(chunk_end))
        )
    )
print("finished saving all-dataset-distribution-data...code complete")
