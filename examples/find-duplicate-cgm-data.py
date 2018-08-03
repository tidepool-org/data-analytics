#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: find duplicate cgm data algorithm
created: 2018-07-24
author: Ed Nykaza
license: BSD-2-Clause
"""

import sys
import os
cwd = os.getcwd()
nameDataAnalyticsRepository = "data-analytics"
packagePath = cwd[:(cwd.find(nameDataAnalyticsRepository) +
                    len(nameDataAnalyticsRepository) + 1)]
sys.path.append(packagePath)
sys.path.append(os.path.join(packagePath, "tpanalyze"))
import tpanalyze as tp
import pandas as pd
import numpy as np
from scipy.signal import correlate
from sklearn.preprocessing import StandardScaler
from itertools import combinations
from math import factorial
import pdb
import time



# %% load in data

hashID = "0289cfb8bd6d61ccf1f31c07aa146b7b14f0eb74474be4311860d9d77dd30f15"

dataPath = os.path.join(".", "data")

data = tp.load_csv(os.path.join(dataPath, hashID + ".csv"))

# %% prepare the data for the algorithm

# work with just the cgm data (though this can be modified for pump data)
cgm = data.loc[data.type == "cbg", ["deviceTime", "time", "value", "uploadId"]]

# convert mmol/L to mg/dL
cgm = cgm.rename(columns={"value": "mmol_L"})
cgm["mg_dL"] = (cgm["mmol_L"] * 18.01559).astype(int)

# round utc time to the nearest 30 seconds, and then to nearest 5 minutes
#cgm = tp.round_time(cgm, 5)

ns5min=5*60*1E9
ns30sec=0.5*60*1E9
cgm["roundedTime30sec"] = pd.to_datetime(cgm["time"]).dt.round("30S")
#    pd.to_datetime((pd.to_datetime(cgm.time).astype(np.int64) // ns30sec) * ns30sec)

cgm["roundedTime5min"] = \
pd.to_datetime((pd.to_datetime(cgm["roundedTime30sec"]).astype(np.int64) // ns5min + 1) * ns5min)




dupList = np.array([9,662,1098,1321,1421,1428,1619,2214,2355,2356,2748,2969,3030,
           3088,3353,3782,4381,4979,5156,5405,5567,5784,6655,6855,7027,
           7472,7498,7614,7618,7673,7772,8142,8817,8872,9800,9989,10077,
           10393,10744,10939,11009,11170,11238,11688,11933,12266,12322,
           12612,13305,14533,14796,14976,15173,15343,15849,16418,16430,
           16741,16816,17069,17269,17370,17475,17725,18161,18423,18599,
           18635,18970,19005,19011,20381,20696,20721,21012,21866,21867,
           21905,22017,22086,23082,23124,23534,24421,24769,25148,25172,
           25505,25621,25785,25941,25986,25995,26047,26442,26659,26769,
           26817,26935,26969,26988,27698,27745,27752,27769,27917,28260,
           28980,29321,29562,29931,30373,30764,30782,30970,31039,31420,
           31558,32518,33278,33570,33628,33948,34247,34824,35266,35406,
           35761,35785,36064,36602,36784,36890,37075,37242,37601,37725,
           37902,38159,38439,38698,38773,38961,39029,39121,39456,39650,
           39789,39821,40374,41743,41878,41950,41999,42124,42133,42461,
           42485,42986,43710,44074,44295,44506,44552,44711,44826,44934,
           45040,45248,45353])


#
#
#import timeit
#import numpy as np
#print(timeit.timeit("5+5"))
#s
#cgm = tp.round_time(cgm, 5)




# %% find duplicate algorithm
results = pd.DataFrame(columns=["uploadId_A", "span_uploadId_A",
                                "n_uploadId_A",
                                "uploadId_B", "span_uploadId_B",
                                "n_uploadId_B", "elapsedTime",
                                "maxCorrelation", "nDuplicates",
                                "averageTimeDifference",
                                "startIndex_A", "endIndex_A",
                                "startIndex_B", "endIndex_B",
                                "dupsWithinFlag_A", "dupsWithinFlag_B",
                                "multipleDupSequencesFlag"])

minThreshold = 96  # 288

## get a list of unique uploadIDs
#uniqueUploads = cgm.uploadId.unique()

# get a count of all the unique uploadIDs
uniqueUploads = pd.DataFrame(cgm.groupby(by="uploadId").mg_dL.count())
uniqueUploads = uniqueUploads.rename(columns={"mg_dL":"counts"})
uniqueUploads = uniqueUploads[uniqueUploads.counts > minThreshold].reset_index()

combos = combinations(uniqueUploads.uploadId, 2)
nCombos = int(factorial(len(uniqueUploads))/(factorial(2) * factorial(len(uniqueUploads) - 2)))
for cIndex, combo in enumerate(list(combos)):

    if cIndex in dupList:
        t = time.time()

        # assign the uploadId with the largest time span to A, and shortest to B
        duration0 = pd.to_datetime(cgm[cgm.uploadId == combo[0]].time.max()) - \
            pd.to_datetime(cgm[cgm.uploadId == combo[0]].time.min())
        duration1 = pd.to_datetime(cgm[cgm.uploadId == combo[1]].time.max()) - \
            pd.to_datetime(cgm[cgm.uploadId == combo[1]].time.min())

        if duration0 >= duration1:
            results.loc[cIndex, ["uploadId_A"]] = combo[0]
            results.loc[cIndex, ["span_uploadId_A"]] = duration0
            results.loc[cIndex, ["n_uploadId_A"]] = \
                uniqueUploads[uniqueUploads.uploadId == combo[0]].counts.values[0]
            results.loc[cIndex, ["uploadId_B"]] = combo[1]
            results.loc[cIndex, ["span_uploadId_B"]] = duration1
            results.loc[cIndex, ["n_uploadId_B"]] = \
                uniqueUploads[uniqueUploads.uploadId == combo[1]].counts.values[0]
        else:
            results.loc[cIndex, ["uploadId_A"]] = combo[1]
            results.loc[cIndex, ["span_uploadId_A"]] = duration1
            results.loc[cIndex, ["n_uploadId_A"]] = \
                uniqueUploads[uniqueUploads.uploadId == combo[1]].counts.values[0]
            results.loc[cIndex, ["uploadId_B"]] = combo[0]
            results.loc[cIndex, ["span_uploadId_B"]] = duration0
            results.loc[cIndex, ["n_uploadId_B"]] = \
                uniqueUploads[uniqueUploads.uploadId == combo[0]].counts.values[0]

        uploadId_A = results.loc[cIndex, "uploadId_A"]
        uploadId_B = results.loc[cIndex, "uploadId_B"]

#        pdb.set_trace()
#
#
#        # %%
#        ## loop through each unique combination of uploadIds
#        ## for now just show example with these two uploadIds
#
#        # this is a great example, becuase there are missign data points
#        uploadId_A = "upid_ff6bf4b6fde9c9bc45bb211de131d225"
#        uploadId_B = "upid_12164f5817e09ab7bffb439d8c260131"
##
#        # %%
        cgm_A = cgm[cgm.uploadId == uploadId_A].reset_index().rename(columns={"index":"originalIndex"})
        cgm_B = cgm[cgm.uploadId == uploadId_B].reset_index().rename(columns={"index":"originalIndex"})

        scaler = StandardScaler()
        scaler = scaler.fit(np.array([cgm_A.mg_dL.astype(float).append(cgm_B.mg_dL.astype(float))]).reshape(-1, 1))
        cgm_A_scaled = scaler.transform(np.array(cgm_A.mg_dL.astype(float)).reshape(-1,1))
        cgm_B_scaled = scaler.transform(np.array(cgm_B.mg_dL.astype(float)).reshape(-1,1))
        xCorr = correlate(cgm_A_scaled, cgm_B_scaled)
        maxCorrelation = xCorr.max()
        results.loc[cIndex, ["maxCorrelation"]] = maxCorrelation
#        print(cIndex, int(maxCorrelation))

        # check for duplicates and flag if there are duplicates within 1 uploadID
        if tp.find_duplicates(cgm_A, "roundedTime5min") > 0:
            results.loc[cIndex, ["dupsWithinFlag_A"]] = tp.find_duplicates(cgm_A, "roundedTime5min")

        if tp.find_duplicates(cgm_B, "roundedTime5min") > 0:
            results.loc[cIndex, ["dupsWithinFlag_B"]] = tp.find_duplicates(cgm_B, "roundedTime5min")

        print(cIndex, int(maxCorrelation),
              tp.find_duplicates(cgm_A, "roundedTime5min"),
              tp.find_duplicates(cgm_B, "roundedTime5min"))

    #    nDuplicates_cgm_A = tp.find_duplicates(cgm_A, "roundedTime5min")
    #    nDuplicates_cgm_B = tp.find_duplicates(cgm_B, "roundedTime5min")
    #
    #    if (nDuplicates_cgm_A > 0) | (nDuplicates_cgm_B > 0):
    #        print("STOP DUPLICATES WITHIN SERIES DETECTED")

        # create a continguous time series from the first to last data point
        contiguousBeginDateTime_A = min(cgm_A.roundedTime5min)
        contiguousEndDateTime_A = max(cgm_A.roundedTime5min)
        rng_A = pd.date_range(contiguousBeginDateTime_A, contiguousEndDateTime_A, freq="5min")
        contiguousData_A = pd.DataFrame(rng_A, columns=["dateTime"])
        # merge data
        contiguousData_A = pd.merge(contiguousData_A, cgm_A,
                                    left_on="dateTime", right_on="roundedTime5min",
                                    how="left")

        contiguousBeginDateTime_B = min(cgm_B.roundedTime5min)
        contiguousEndDateTime_B = max(cgm_B.roundedTime5min)
        rng_B = pd.date_range(contiguousBeginDateTime_B, contiguousEndDateTime_B, freq="5min")
        contiguousData_B = pd.DataFrame(rng_B, columns=["dateTime"])
        # merge data
        contiguousData_B = pd.merge(contiguousData_B, cgm_B,
                                    left_on="dateTime", right_on="roundedTime5min",
                                    how="left")

        TL = np.array(contiguousData_A.mg_dL)
        Ts = np.array(contiguousData_B.mg_dL)

        # add NaNs to the beginning and end of TL
        addNaNs = np.repeat(np.nan, len(Ts) - minThreshold)
        n_addNaNs = len(addNaNs)

        TL = np.append(addNaNs, TL)
        TL = np.append(TL, addNaNs)

        j = 0
        for i in range(0, len(TL) - len(Ts)):
    ## %% time it
    #s = """\
    #import numpy as np
    #import pandas as pd
    #tempDiff = np.zeros(10000) - np.ones(10000)
    #
    #"""
    #timeit.timeit(stmt=s, number=100000)
    #
    ## tempDiff = np.zeros(10000) - np.ones(10000) THIS IS 10 TIMES FASTER THAN:
    ## tempDiff = pd.Series(np.zeros(10000)) - pd.Series(np.ones(10000))
    #
    ### tempDiff = np.zeros(1000) - np.ones(1000) takes 0.51 seconds for 100,000 iterations
    ### tempDiff = np.subtract(np.zeros(1000), np.ones(1000)) takes 0.53
    ## %%

            tempDiff = TL[i:(len(Ts) + i)] - Ts
            nZeros = sum(tempDiff == 0)
            if nZeros >= minThreshold:
                j = j + 1
                print(cIndex, i, nZeros)
                duplicateStartIndex = i
                duplicateEndIndex = len(Ts) + i
                duplicatedSequence = TL[duplicateStartIndex:duplicateEndIndex]

                if (i - n_addNaNs) < 0:
                    dupTs = contiguousData_B[(n_addNaNs - i):]
                    dupTL = contiguousData_A[:(len(dupTs))]
                    print("case 1, Ts before TL")

                else:
                    if (i + len(Ts)) < len(TL):
                        dupTs = contiguousData_B
                        dupTL = contiguousData_A[(i - n_addNaNs):((i - n_addNaNs) + (len(dupTs)))]
                        print("case 2, Ts within TL")
                    else:
                        dupTL = contiguousData_A[(i - n_addNaNs):(n_addNaNs + len(TL))]
                        dupTs = contiguousData_B[:(len(dupTL))]
                        print("case 3, Ts extends TL")
                        pdb.set_trace()

    #            dupTL = contiguousData_A[(i - n_addNaNs):(i - n_addNaNs + len(Ts))]
    #            dupTs = contiguousData_B
                combined = pd.concat([dupTL.reset_index(drop=True).add_suffix(".TL"),
                                    dupTs.reset_index(drop=True).add_suffix(".Ts")], axis=1)

                results.loc[cIndex, ["nDuplicates"]] = nZeros
                results.loc[cIndex, ["startIndex_A"]] = \
                    combined.loc[combined["mg_dL.TL"].notnull(), "originalIndex.TL"].min()
                results.loc[cIndex, ["endIndex_A"]] = \
                    combined.loc[combined["mg_dL.TL"].notnull(), "originalIndex.TL"].max()

                results.loc[cIndex, ["startIndex_B"]] = \
                    combined.loc[combined["mg_dL.Ts"].notnull(), "originalIndex.Ts"].min()
                results.loc[cIndex, ["endIndex_B"]] = \
                    combined.loc[combined["mg_dL.Ts"].notnull(), "originalIndex.Ts"].max()

                cTimeDifference = pd.to_datetime(combined["time.TL"]) - \
                                    pd.to_datetime(combined["time.Ts"])

                averageTimeDifference = cTimeDifference.dt.seconds.mean()
                results.loc[cIndex, ["averageTimeDifference"]] = averageTimeDifference


#                pdb.set_trace()
                if j > 1:
                    results.loc[cIndex, ["multipleDupSequencesFlag"]] = j

        elapsedTime = time.time() - t
        results.loc[cIndex, ["elapsedTime"]] = elapsedTime
        print("finished ", cIndex, "of",
              int(nCombos), "(", round((cIndex + 1) / nCombos*100, 1), "%) ",
              "spanA = ", results.loc[cIndex, "span_uploadId_A"],
              "spanB = ", results.loc[cIndex, "span_uploadId_B"],
              " time elapsed = ", round(elapsedTime, 1), "secs")


#        pdb.set_trace()

results.to_csv(os.path.join(dataPath, "dup-results-" + hashID + "-v5NewRoundedTime.csv"))



# %%

#scaler = StandardScaler()
#scaler = scaler.fit(np.array([cgm_A.mg_dL.astype(float).append(cgm_B.mg_dL.astype(float))]).reshape(-1, 1))
#cgm_A_scaled = scaler.transform(np.array(cgm_A.mg_dL.astype(float)).reshape(-1,1))
#cgm_B_scaled = scaler.transform(np.array(cgm_B.mg_dL.astype(float)).reshape(-1,1))
#xCorr = correlate(cgm_A_scaled, cgm_B_scaled)
#maxCorrelation = xCorr.max()
#lag = np.argmax(xCorr)
#c_sig = np.roll(cgm_B.mg_dL, shift=int(np.ceil(lag)))
