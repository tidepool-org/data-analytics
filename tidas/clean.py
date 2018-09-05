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
    df = df.loc[~(criteriaDF.duplicated())]
    df = df.reset_index(drop=True)
    nDuplicatesRemoved = nBefore - len(df)

    return df, nDuplicatesRemoved


def round_time(df, timeInterval):

    # first round to the nearest 30 seconds, which addresses edge case when
    # data occurs right near increments of 2:30. For example, if cgm data
    # occurs at 2:30 and 7:29, they both get rounded to 5:00
    df["roundedTime"] = pd.DatetimeIndex(df["time"]).round("30S")

    # then round to the nearest user defined minutes
    # (e.g., 5 or 15 minutes for cgm data)
    df["roundedTime"] = df["roundedTime"].dt.round(str(timeInterval) + "min")

    return df
