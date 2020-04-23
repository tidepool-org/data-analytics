#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# %% REQUIRED LIBRARIES
import datetime as dt
import pandas as pd
import os
import glob
import argparse


# %% FUNCTIONS
def get_dataset_summaries(
        save_data_path=os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "data"
            )
        ),
        date_stamp=dt.datetime.now().strftime("%Y-%m-%d"),
):



    phi_date_stamp = "PHI-" + args.date_stamp
    donor_folder = os.path.join(args.data_path, phi_date_stamp + "-donor-data")

    print("combining all dataset metadata")

    metadata_path = os.path.join(
        args.data_path,
        phi_date_stamp + "-donor-data",
        phi_date_stamp + "-datasetSummary"
    )

    all_files = glob.glob(os.path.join(metadata_path, "*.csv.gz"))
    dataset_metadata = pd.DataFrame()
    n_files = len(all_files)
    print("there are {} files".format(n_files))
    f_counter = 1
    for f in all_files:
        temp_meta = pd.read_csv(f)
        temp_meta.rename(columns={"Unnamed: 0": "col_name"}, inplace=True)
        userid = f[-32:-22]
        temp_meta["userid"] = userid
        dataset_metadata = pd.concat(
            [dataset_metadata, temp_meta],
            ignore_index=True,
            sort=False
        )

        if f_counter % 10 == 0:
            print("completed file {} of {}".format(f_counter, n_files))
        f_counter = f_counter + 1
    dataset_metadata.to_csv(
        os.path.join(donor_folder, phi_date_stamp + "-all-dataset-info.csv.gz")
    )
    print("saving all-dataset-info-metadata...code complete")

    return


# %% MAIN
if __name__ == "__main__":
    # USER INPUTS (choices to be made in order to run the code)
    codeDescription = "get donor json file"
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

    args = parser.parse_args()

    # the main function
    get_dataset_summaries(
        save_data_path=args.data_path,
        date_stamp=args.date_stamp
    )
