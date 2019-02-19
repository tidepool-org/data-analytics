#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# %% REQUIRED LIBRARIES
import argparse
from loop_report import LoopReport
import pandas as pd
import json
import os
import datetime as dt


# %% CODE DESCRIPTION
codeDescription = (
    "Parses Loop issue report(s) into a dictionary," +
    "and saves the data to user specified format (json or csv)"
)


# %% FUNCTIONS
def parse_by_file(file_path, file_name, output_path):

    if not os.path.isfile(os.path.join(file_path, file_name)):
        raise RuntimeError("The file name is invalid.")

    # make an output folder if it does not exist
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # % parse file
    lr = LoopReport()
    loop_dict = lr.parse_by_file(path=file_path, file_name=file_name)

    # save a pretty json
    output_path_name = os.path.join(
        output_path, file_name[:-3] + "-parsed.json"
    )

    with open(output_path_name, "w") as fp:
        json.dump(loop_dict, fp, sort_keys=True, indent=4)

    print(file_name, "file parsed")

    return loop_dict


def parse_directory(file_path, output_path):
    all_loop_df = pd.DataFrame()
    for file in os.listdir(args.file_path):
        if ".md" in file:
            loop_dict = parse_by_file(file_path, file, output_path)

            loop_df = pd.DataFrame(columns=loop_dict.keys(), index=[0])
            loop_df = loop_df.astype("object")
            for k in loop_dict.keys():
                loop_df[k][0] = loop_dict[k]

            all_loop_df = pd.concat(
                [all_loop_df, loop_df],
                sort=False,
                ignore_index=True)

            process_date = dt.datetime.now().strftime("%Y-%m-%d")
            output_path_name = os.path.join(
                output_path, process_date + "-batch-parsing.csv"
            )

            all_loop_df.to_csv(output_path_name, index_label="index")

    return all_loop_df


# %% COMMAND LINE ARGUMENTS
def main(args):

    if not os.path.isdir(args.file_path):
        raise RuntimeError("The file path is invalid.")

    if args.batch_process:  # process all md files in path
        output = parse_directory(args.file_path, args.output_path)

    else:  # process one file
        output = parse_by_file(
            args.file_path,
            args.file_name,
            args.output_path
        )

    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=codeDescription)
    parser.add_argument(
        "-p",
        "--path",
        dest="file_path",
        default=os.path.join("..", "tests", "parsers", "files"),
        help="directory of the issue report file(s)"
    )
    parser.add_argument(
        "-n",
        "--file_name",
        dest="file_name",
        default="LoopReport.md",
        help="directory of the issue report file(s)"
    )
    parser.add_argument(
        "-o",
        "--output_path",
        dest="output_path",
        default=os.path.join(".", "output", ""),
        help="directory of where to save the output file(s)"
    )
    parser.add_argument(
        "-b",
        "--batch",
        dest="batch_process",
        default=True,
        help="True if you want to process all issue reports in the dir",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose_output",
        default=True,
        help="True if you want script progress to print to the console",
    )
    args = parser.parse_args()

    output = main(args)
