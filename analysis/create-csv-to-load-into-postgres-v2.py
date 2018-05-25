#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: Load donor data in xlsx format into pandas
version: 0.0.1
created: 2018-05-10
author: Ed Nykaza
dependencies:
    * requires tidepool analysis environment (see readme for instructions), OR
it requires that the xlrd module is installed in your environment

license: BSD-2-Clause
"""

import pandas as pd
import glob

# grab all of the anonymized datasets
dataPath = "/ed/projects/data-analytics/data/"
anonymizedPath = "Tidepool Example Data v2018-05-09/"
xlsxExportFolder = dataPath + anonymizedPath + "xlsx/"
xlsxFilePaths = glob.glob(xlsxExportFolder + "*.xlsx")
for i in range(0,len(xlsxFilePaths)):

    hashID = xlsxFilePaths[i][72:-5]
    xlsxPathAndFileName = xlsxFilePaths[i]

    # load xlsx
    df = pd.read_excel(xlsxPathAndFileName, sheet_name=None, ignore_index=True)
    cdf = pd.concat(df.values(), ignore_index=True)
    cdf = cdf.set_index('jsonRowIndex')

    # add the hashID
    cdf["hashID"] = hashID

    ## save as csv file
    outpath = dataPath + anonymizedPath + "csv/" + hashID
    cdf.to_csv(outpath + ".csv")
    cdf.to_json(outpath + ".json")
    print("finshed with file number", i)
