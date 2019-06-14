#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# %% REQUIRED LIBRARIES
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import argparse
import pdb

# %% CODE DESCRIPTION
codeDescription = (
    "simulate ysi values from iCGM values using the reported distributions" +
    "in Table 3A and 4A from the " +
    "Dexcom G6 Continuous Glucose Monitoring System User Guide:"
    "https://s3-us-west-2.amazonaws.com/dexcompdf/G6-CGM-Users-Guide.pdf"
)


# %% FUNCTIONS
#def main_function():
#    return


# %% START OF CODE
# seed the random number generator for repeatability
np.random.seed(seed=0)

# load in data (first just make up some data, and later real iCGM data)
icgm_values = np.arange(40, 400, 5)

# then load in distributions for adults using dexcom g6
adult_val_prob = pd.read_csv(
  "dex-g6-adult-ysi-value-probabilities.csv"
)

#adult_rate_probabilities = pd.read_csv("dex-g6-adult-rate-probabilities.csv")

for icgm in icgm_values:
    # get the ysi probabilities for each icgm
    ysi_headings_list = list(adult_val_prob)[4:]
    ysi_headings_array = np.array(ysi_headings_list).reshape((1, 11))
    ysi_row = (
      (icgm >= adult_val_prob["icgmLow"]) &
      (icgm <= adult_val_prob["icgmHigh"])
    )

    ysi_col = adult_val_prob.loc[ysi_row, ysi_headings_list].notnull().values

    ysi = pd.DataFrame(
      data=adult_val_prob.loc[ysi_row, ysi_headings_array[ysi_col]].values.T,
      columns=["prob"]
    )
    ysi["cumsum"] = ysi["prob"].cumsum()
    ysi["low"] = adult_val_prob.loc[0, ysi_headings_array[ysi_col]].values
    ysi["high"] = adult_val_prob.loc[1, ysi_headings_array[ysi_col]].values

    # randomly draw from a uniform distribution to figure out
    # which bin the ysi value should come from
    r = np.random.uniform()
    bin = ((r <= ysi["cumsum"]) & (r > ysi["cumsum"].shift(1).fillna(0)))
    print(r, "\n", ysi.loc[bin])
    ysi_value = np.random.randint(
        low=ysi.loc[bin, "low"],
        high=ysi.loc[bin, "high"]+1,  # +1 because high value is exclusive
    )
    print(icgm, ysi_value, "\n")

# %% delete later
s = np.random.uniform(0., 1., 100000)
count, bins, ignored = plt.hist(s, 15, density=True)
plt.plot(bins, np.ones_like(bins), linewidth=2, color='r')
plt.show()
# %% COMMAND LINE ARGUMENTS
#def main(args):
#    main_function(args)
#
#
#if __name__ == "__main__":
#    parser = argparse.ArgumentParser(description=codeDescription)
##    parser.add_argument(
##        "-<single letter>",
##        "--<longer description>",
##        dest="<vairable_name>",
##        default=<default_variable_value>,
##        help="<help descripition>"
##    )
#
#    args = parser.parse_args()
#
#    main(args)

