#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: Example code using the loop_report class.
Created on Fri Jan 25 06:55:48 2019

@author: ed

commandline example to run the parser :
python parser_client.py ../tests/parsers/files LoopReport.md
"""

from loop_report import LoopReport
import pandas as pd
import json
import os
import sys


def parse_by_file(file_path, file_name):

    output_path = os.path.join(".", "output")
    # make an output folder if it does not exist
    if not os.path.exists(output_path):
        os.makedirs(output_path)


    # %% parse file
    lr = LoopReport()
    loop_dict = lr.parse_by_file(path=file_path, file_name=file_name)


    # %% put data into a dataframe and save
    loop_df = pd.DataFrame(columns=loop_dict.keys(), index=[0])
    loop_df = loop_df.astype("object")
    for k in loop_dict.keys():
        loop_df[k][0] = loop_dict[k]

    loop_df.to_csv(
        os.path.join(output_path, file_name + "-data-in-columns.csv"), index_label="index"
    )
    loop_df.T.to_csv(
        os.path.join(output_path, file_name + "-data-in-rows.csv"), index_label="index"
    )

    output_path = os.path.join("./", "output/")
    # %% if we remove the embedded data frames, we can save a pretty json
    with open(output_path + file_name + "-data.json", "w") as fp:
        json.dump(loop_dict, fp, sort_keys=True, indent=4)

    print("file parsed")


def main():
    file_path = sys.argv[1]
    file_name = sys.argv[2]
    if not os.path.isdir(file_path):
        raise RuntimeError("The file path is invalid.")

    if not os.path.isfile(f"{file_path}/{file_name}"):
        raise RuntimeError("The file name is invalid.")

    parse_by_file(file_path, file_name)

if __name__ == "__main__":
    main()