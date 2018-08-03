#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: load csv data
created: 2018-02-21
author: Ed Nykaza
license: BSD-2-Clause
"""

import pandas as pd


def remove_duplicates(df, criteriaDF):
    nBefore = len(df)
    df = df.loc[~(df[criteriaDF].duplicated())]
    df = df.reset_index(drop=True)
    nDuplicatesRemoved = nBefore - len(df)

    return df, nDuplicatesRemoved


def find_duplicates(df, criteriaDF):
    df, nDuplicates = remove_duplicates(df, criteriaDF)

    return nDuplicates


def round_time(df, timeInterval):

    # first round to the nearest 30 seconds, which addresses edge case when
    # data occurs right near increments of 2:30. For example, if cgm data
    # occurs at 2:30 and 7:29, they both get rounded to 5:00
    df["roundedTime30s"] = (pd.to_datetime(df["time"]).dt.round("30S"))  # + pd.Timedelta(milliseconds=1)

    # then round to the nearest user defined minutes
    # (e.g., 5 or 15 minutes for cgm data)
    df["roundedTime5min"] = df["roundedTime30s"].dt.round(str(timeInterval) + "min")

    return df
