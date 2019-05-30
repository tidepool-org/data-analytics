# -*- coding: utf-8 -*-
"""accept_donors_and_pull_data.py
This is a wrapper script that qualifies all bigdata donation project donors.
"""

# %% REQUIRED LIBRARIES
import datetime as dt
import os
import argparse
import time
import subprocess as sub
import pandas as pd
from multiprocessing import Pool


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


# %% FUNCTIONS
def qualify_data(userid):

    qualify_path = os.path.join(
        ".", "qualify_single_dataset.py"
    )

    p = sub.Popen(
        [
             "python", qualify_path,
             "-d", args.date_stamp,
             "-u", userid,
             "-o", args.data_path
         ],
        stdout=sub.PIPE,
        stderr=sub.PIPE
    )

    output, errors = p.communicate()
    output = output.decode("utf-8")
    errors = errors.decode("utf-8")

    if errors == '':
        print(output)
    else:
        print(errors)

    return


# %% START OF CODE
date_stamp = args.date_stamp
phi_date_stamp = "PHI-" + date_stamp
donor_folder = os.path.join(args.data_path, phi_date_stamp + "-donor-data")

uniqueDonorList_path = os.path.join(
    donor_folder,
    phi_date_stamp + "-uniqueDonorList.csv"
)

final_donor_list = pd.read_csv(uniqueDonorList_path, low_memory=False)

# use multiple cores to process
startTime = time.time()
print("starting at " + dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
pool = Pool(os.cpu_count())
pool.map(qualify_data, final_donor_list.userID.values)
pool.close()

endTime = time.time()
print("finshed at " + dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
total_duration = round((endTime - startTime) / 60, 1)
print("total duration was %s minutes" % total_duration)
