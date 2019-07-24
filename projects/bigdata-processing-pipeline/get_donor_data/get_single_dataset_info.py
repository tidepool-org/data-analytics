# -*- coding: utf-8 -*-
"""get_donor_data_and_metadata.py
This code takes a tidepool dataset as input, and gives
a description of the type of data in the dataset.
"""


# %% REQUIRED LIBRARIES
import pandas as pd
import datetime as dt
import numpy as np
import os
import ast
import argparse


# %% FUNCTIONS
def get_type(val):
    return type(val).__name__


def get_len(val):
    return len(val)


def get_val(val, k):
    return val[k]


def literal_return(val):
    try:
        return ast.literal_eval(val)
    except (ValueError, SyntaxError):
        return val


def remove_cols(df, cols_to_remove):

    temp_remove_cols = list(set(df) & set(cols_to_remove))
    tempDf = df[temp_remove_cols]
    df = df.drop(columns=temp_remove_cols)

    return df, tempDf


def make_folder_if_doesnt_exist(folder_paths):
    ''' function requires a single path or a list of paths'''
    if not isinstance(folder_paths, list):
        folder_paths = [folder_paths]
    for folder_path in folder_paths:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
    return


def create_output_folder(
        data_path,
        date_stamp,
        folder_name,
        phi=True
):
    if phi:
        date_stamp = "PHI-" + date_stamp
    donor_folder = os.path.join(data_path, date_stamp + "-donor-data")
    dataset_path = os.path.join(
        donor_folder,
        date_stamp + "-" + folder_name
    )
    make_folder_if_doesnt_exist(dataset_path)

    return dataset_path


def save_df(
        df,
        userid,
        data_path,
        date_stamp,
        folder_name,
        phi=True,
        name_suffix="",
):

    output_folder = create_output_folder(
        data_path=data_path,
        date_stamp=date_stamp,
        folder_name=folder_name,
        phi=phi
    )

    # if the data contains phi, add prefix to the file
    if phi:
        phi_prefix = 'PHI-'
    else:
        phi_prefix = ''
    output_path = os.path.join(
        output_folder,
        phi_prefix + userid + "{}.csv.gz".format(name_suffix)
    )

    df.to_csv(output_path)

    return output_path


def expand_df(df, do_not_expand_list=[]):

    # remove fields that we don't want to flatten
    df, hold_df = remove_cols(df, do_not_expand_list)

    # get a description of the original columns
    col_df = pd.DataFrame(df.dtypes, columns=["dtype"])

    # go through each dtype that is an object to see if it
    # contains strings, mixed datatypes, embedded json, or lists
    col_df["nObjectTypes"] = np.nan
    col_df["objectType"] = np.nan

    new_df = pd.DataFrame()
    for col in col_df[col_df["dtype"] == "object"].index:
        rows = df.index[df[col].notnull()].tolist()

        # sometimes the object gets wrapped in a string
        literal_df = pd.DataFrame(df.loc[rows, col].apply(literal_return))

        # see if there are mixed ojbect types
        type_df = pd.DataFrame(literal_df.loc[rows, col].apply(get_type))
        unique_types = type_df[col].unique()
        col_df.loc[col, "nObjectTypes"] = len(unique_types)
        col_df.loc[col, "objectType"] = str(unique_types)

        # USE UNDERSCORE FOR LIST EXPANSION
        if "list" in col_df.loc[col, "objectType"]:
            list_df = pd.DataFrame(literal_df.loc[type_df[col] == "list", col])
            list_df["len"] = list_df[col].apply(get_len)

            for i in np.arange(1, list_df["len"].max() + 1):
                blob_df = pd.DataFrame(
                    list_df.loc[
                        list_df["len"] >= i, col
                        ].apply(get_val, k=i-1)
                    ).add_suffix('_' + str(i))

                new_df = pd.concat([new_df, blob_df], axis=1)

        # USE DOT FOR JSON (DICT) EXPANSION
        if "dict" in col_df.loc[col, "objectType"]:
            json_blob = literal_df.loc[type_df[col] == "dict", col]
            blob_df = pd.DataFrame(
                json_blob.tolist(),
                index=json_blob.index
            ).add_prefix(col + '.')
            new_df = pd.concat([new_df, blob_df], axis=1)

    # merge the dataframes together
    df = pd.concat([df, new_df, hold_df], axis=1)

    df.sort_index(axis=1, inplace=True)

    return df, col_df


def expand_data(starting_df, depth=10):
    print("\ninitial df has {} columns".format(len(starting_df.columns)))
    print("starting expansion ...")
    temp_df, temp_col = expand_df(starting_df)
    col_df = temp_col.copy()
    skip_columns = starting_df.columns.tolist()
    d = 1
    n_col_expanded = len(list(temp_df)) - len(list(starting_df))
    print("{} columns added". format(n_col_expanded))

    while not ((d >= depth) | (len(temp_col) == 0)):
        print("expanding layer {} ... ".format(d))
        next_skip_columns = temp_df.columns.tolist()
        temp_df, temp_col = expand_df(temp_df, skip_columns)
        skip_columns = next_skip_columns.copy()

        col_df = pd.concat([col_df, temp_col])
        n_col_expanded = len(list(temp_df)) - len(next_skip_columns)
        print("{} columns added". format(n_col_expanded))
        d += 1

    print("expansion complete...getting dataset summary info...")

    col_df.sort_index(inplace=True)

    # get the start and end time for each data type
    print("getting data start and end times for each data type ...")
    col_df["startTime"] = np.nan
    col_df["endTime"] = np.nan
    for col in col_df.index:
        try:
            start_time = temp_df.loc[temp_df[col].notnull(), ["time"]].min()
            end_time = temp_df.loc[temp_df[col].notnull(), ["time"]].max()
            col_df.loc[col, "startTime"] = start_time.values[0]
            col_df.loc[col, "endTime"] = end_time.values[0]
        except:
            print(col, "missing timestamp")

    # get summary information
    print("getting summary information ...")
    df_info = pd.DataFrame(temp_df.describe(include='all').T)
    df_info.loc["_all", ["count", "unique"]] = temp_df.shape
    df_info.sort_index(inplace=True)

    # add which type (or subtype) each column comes from
    for typeType in ["type", "subType"]:
        if typeType in list(starting_df):
            type_groups = temp_df.groupby(by=typeType)
            not_null_index = temp_df[typeType].notnull()
            for type_ in temp_df.loc[not_null_index, typeType].unique():
                type_df = type_groups.get_group(type_).dropna(
                    axis=1,
                    how="all"
                )
                df_info.loc[type_df.columns, typeType + "=" + type_] = type_

    # get memory size of each data type
    print("getting memory information ...")
    mem_usage = pd.DataFrame(
        temp_df.memory_usage(index=True, deep=True),
        columns=["memorySize"]
    )
    mem_usage.rename(index={"Index": "_all"}, inplace=True)
    df_info["memorySize"] = mem_usage["memorySize"]
    df_info.loc["_all", "memorySize"] = temp_df.memory_usage(
        index=True, deep=True
    ).sum()

    # combine with col_summary
    summary_df = pd.concat([col_df, df_info], axis=1, sort=True)

    # get/add a list of string values
    print("getting a a list of string values ...")
    str_cols = summary_df[
        ((summary_df["objectType"] == "['str']") &
         (summary_df["unique"] > 1) &
         (summary_df["unique"] < 50)
        )
    ].index
    for str_col in str_cols:
        not_null_index = temp_df[str_col].notnull()
        str_vals = temp_df.loc[not_null_index, str_col].unique().tolist()
        summary_df.loc[str_col, "strVals"] = str(str_vals)

    print("dataset summary info complete\n")

    return summary_df, temp_df


# %% START OF CODE
def get_dataset_info(
    data,
    date_stamp,
    data_path,
    userid,
    save_expanded
):

    if userid == "not-specified":
        userid = input("Enter userid of dataset you want info on:\n")

    if type(data) is float:  # np.nan is a float
        dataset_folder = create_output_folder(
            data_path,
            date_stamp,
            "csvData"
        )
        dataset_path = os.path.join(
            dataset_folder,
            "PHI-{}.csv.gz".format(userid)
        )
        data = pd.read_csv(dataset_path, low_memory=False, index_col=0)

    # expand embedded lists and json within dataset
    summary_df, expanded_df = expand_data(data.copy(), depth=10)

    # save summary data
    _ = save_df(
        summary_df,
        userid=userid,
        data_path=data_path,
        date_stamp=date_stamp,
        folder_name="datasetSummary",
        phi=True,
        name_suffix="-datasetSummary"
    )

    if save_expanded:
        # save expanded data
        _ = save_df(
            expanded_df,
            userid=userid,
            data_path=args.data_path,
            date_stamp=args.date_stamp,
            folder_name="expandedData",
            phi=True,
            name_suffix="-expandedData"
        )


if __name__ == "__main__":
    # USER INPUTS (choices to be made in order to run the code)
    codeDescription = "get an overview of the columns and data in the dataset"
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
        "-u",
        "--userid",
        dest="userid",
        default="not-specified",
        help="userid of the dataset you are interested in"
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
        "--save-expanded-dataset",
        dest="save_expanded",
        default=True,
        help=(
            "specify if you want to save the expanded datafram (True/False)"
            + "NOTE: these files can be rather large"
        )
    )

    args = parser.parse_args()

    # main function
    get_dataset_info(
        data=np.nan,
        date_stamp=args.date_stamp,
        data_path=args.data_path,
        userid=args.userid,
        save_expanded=args.save_expanded
    )
