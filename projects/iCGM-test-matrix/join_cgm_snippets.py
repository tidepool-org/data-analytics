# %% REQUIRED LIBRARIES
import os
import sys
import requests
import json
import getpass
import random
import numpy as np
import pandas as pd
import datetime as dt
from pytz import timezone
from scipy import stats
from scipy.optimize import curve_fit
import plotly.graph_objs as go
from plotly.offline import iplot, plot
import matplotlib.pyplot as plt
import plotly.express as px

# %% FUNCTIONS
def mmolL_to_mgdL(mmolL):
    return mmolL * 18.01559


def remove_timezone(local_timezoneAware):
    local_time = local_timezoneAware.tz_localize(None)
    return local_time


def getStartAndEndTimes(df, dateTimeField):
    dfBeginDate = df[dateTimeField].min()
    dfEndDate = df[dateTimeField].max()

    return dfBeginDate, dfEndDate


def removeDuplicates(df, criteriaDF):
    nBefore = len(df)
    df = df.loc[~(df[criteriaDF].duplicated())]
    df = df.reset_index(drop=True)
    nDuplicatesRemoved = nBefore - len(df)

    return df, nDuplicatesRemoved

def removeCgmDuplicates(df, timeCriterion):
    if timeCriterion in df:
        df.sort_values(by=[timeCriterion, "uploadTime"],
                       ascending=[False, False],
                       inplace=True)
        dfIsNull = df[df[timeCriterion].isnull()]
        dfNotNull = df[df[timeCriterion].notnull()]
        dfNotNull, nDuplicatesRemoved = removeDuplicates(dfNotNull, [timeCriterion, "value"])
        df = pd.concat([dfIsNull, dfNotNull])
        df.sort_values(by=[timeCriterion, "uploadTime"],
                       ascending=[False, False],
                       inplace=True)
    else:
        nDuplicatesRemoved = 0

    return df, nDuplicatesRemoved

def add_uploadDateTime(df):
    if "upload" in data.type.unique():
        uploadTimes = pd.DataFrame(
            df[df.type == "upload"].groupby("uploadId").time.describe()["top"]
        )
    else:
        uploadTimes = pd.DataFrame(columns=["top"])
    # if an upload does not have an upload date, then add one
    # NOTE: this is a new fix introduced with healthkit data...we now have
    # data that does not have an upload record
    unique_uploadIds = set(df["uploadId"].unique())
    unique_uploadRecords = set(
        df.loc[df["type"] == "upload", "uploadId"].unique()
    )
    uploadIds_missing_uploadRecords = unique_uploadIds - unique_uploadRecords

    for upId in uploadIds_missing_uploadRecords:
        last_upload_time = df.loc[df["uploadId"] == upId, "time"].max()
        uploadTimes.loc[upId, "top"] = last_upload_time

    uploadTimes.reset_index(inplace=True)
    uploadTimes.rename(
        columns={
            "top": "uploadTime",
            "index": "uploadId"
        },
        inplace=True
    )
    df = pd.merge(df, uploadTimes, how='left', on='uploadId')
    df["uploadTime"] = pd.to_datetime(df["uploadTime"])

    return df

def round_time(df, timeIntervalMinutes=5, timeField="time",
               roundedTimeFieldName="roundedTime", startWithFirstRecord=True,
               verbose=False):
    '''
    A general purpose round time function that rounds the "time"
    field to nearest <timeIntervalMinutes> minutes
    INPUTS:
        * a dataframe (df) that contains a time field that you want to round
        * timeIntervalMinutes (defaults to 5 minutes given that most cgms output every 5 minutes)
        * timeField to round (defaults to the UTC time "time" field)
        * roundedTimeFieldName is a user specified column name (defaults to roundedTime)
        * startWithFirstRecord starts the rounding with the first record if True, and the last record if False (defaults to True)
        * verbose specifies whether the extra columns used to make calculations are returned
    '''

    df.sort_values(by=timeField, ascending=startWithFirstRecord, inplace=True)
    df.reset_index(drop=True, inplace=True)

    # make sure the time field is in the right form
    t = pd.to_datetime(df[timeField])

    # calculate the time between consecutive records
    t_shift = pd.to_datetime(df[timeField].shift(1))
    df["timeBetweenRecords"] = \
        round((t - t_shift).dt.days*(86400/(60 * timeIntervalMinutes)) +
              (t - t_shift).dt.seconds/(60 * timeIntervalMinutes)) * timeIntervalMinutes

    # separate the data into chunks if timeBetweenRecords is greater than
    # 2 times the <timeIntervalMinutes> minutes so the rounding process starts over
    largeGaps = list(df.query("abs(timeBetweenRecords) > " + str(timeIntervalMinutes * 2)).index)
    largeGaps.insert(0, 0)
    largeGaps.append(len(df))

    for gIndex in range(0, len(largeGaps) - 1):
        chunk = t[largeGaps[gIndex]:largeGaps[gIndex+1]]
        firstRecordChunk = t[largeGaps[gIndex]]

        # calculate the time difference between each time record and the first record
        df.loc[largeGaps[gIndex]:largeGaps[gIndex+1], "minutesFromFirstRecord"] = \
            (chunk - firstRecordChunk).dt.days*(86400/(60)) + (chunk - firstRecordChunk).dt.seconds/(60)

        # then round to the nearest X Minutes
        # NOTE: the ".000001" ensures that mulitples of 2:30 always rounds up.
        df.loc[largeGaps[gIndex]:largeGaps[gIndex+1], "roundedMinutesFromFirstRecord"] = \
            round((df.loc[largeGaps[gIndex]:largeGaps[gIndex+1],
                          "minutesFromFirstRecord"] / timeIntervalMinutes) + 0.000001) * (timeIntervalMinutes)

        roundedFirstRecord = (firstRecordChunk + pd.Timedelta("1microseconds")).round(str(timeIntervalMinutes) + "min")
        df.loc[largeGaps[gIndex]:largeGaps[gIndex+1], roundedTimeFieldName] = \
            roundedFirstRecord + \
            pd.to_timedelta(df.loc[largeGaps[gIndex]:largeGaps[gIndex+1],
                                   "roundedMinutesFromFirstRecord"], unit="m")

    # sort by time and drop fieldsfields
    df.sort_values(by=timeField, ascending=startWithFirstRecord, inplace=True)
    df.reset_index(drop=True, inplace=True)
    if verbose is False:
        df.drop(columns=["timeBetweenRecords",
                         "minutesFromFirstRecord",
                         "roundedMinutesFromFirstRecord"], inplace=True)

    return df

def get_data_from_api(
    email=np.nan,
    password=np.nan,
    weeks_of_data=4,
    userid_of_shared_user=np.nan,
):

    if pd.isnull(email):
        email=input("Enter the email address of your Tidepool account:\n")

    if pd.isnull(password):
        password=getpass.getpass("Enter the password of your Tidepool account:\n")

    print("\nGetting the last %d weeks of data..." % weeks_of_data)

    df = pd.DataFrame()
    url1 = "https://api.tidepool.org/auth/login"
    url3 = "https://api.tidepool.org/auth/logout"

    myResponse = requests.post(url1, auth=(email, password))

    if(myResponse.ok):
        xtoken = myResponse.headers["x-tidepool-session-token"]

        if pd.isnull(userid_of_shared_user):
            userid = json.loads(myResponse.content.decode())["userid"]
        else:
            userid = userid_of_shared_user

        endDate = pd.datetime.now()

        if weeks_of_data > 52:
            years_of_data = int(np.floor(weeks_of_data / 52))
            for years in range(0, years_of_data + 1):
                startDate = endDate - pd.Timedelta(365, unit="d")
                print(years, startDate, endDate)
                url2 = "https://api.tidepool.org/data/" + userid + \
                    "?endDate=" + endDate.strftime("%Y-%m-%d") + \
                    "T23:59:59.000Z&startDate=" + \
                    startDate.strftime("%Y-%m-%d") + "T00:00:00.000Z"

                headers = {
                    "x-tidepool-session-token": xtoken,
                    "Content-Type": "application/json"
                    }

                myResponse2 = requests.get(url2, headers=headers)
                if(myResponse2.ok):

                    usersData = json.loads(myResponse2.content.decode())
                    tempDF = pd.DataFrame(usersData)
                    df = pd.concat([df, tempDF], ignore_index=True)

                else:
                    print("ERROR in year ", years, myResponse2.status_code)

                endDate = startDate - pd.Timedelta(1, unit="d")


        else:
            startDate = endDate - pd.Timedelta(weeks_of_data*7, unit="d")
            url2 = "https://api.tidepool.org/data/" + userid + \
                "?endDate=" + endDate.strftime("%Y-%m-%d") + \
                "T23:59:59.000Z&startDate=" + \
                startDate.strftime("%Y-%m-%d") + "T00:00:00.000Z"

            headers = {
                "x-tidepool-session-token": xtoken,
                "Content-Type": "application/json"
                }

            myResponse2 = requests.get(url2, headers=headers)
            if(myResponse2.ok):
                usersData = json.loads(myResponse2.content.decode())
                df = pd.DataFrame(usersData)
            else:
                print("ERROR in getting data ", myResponse2.status_code)
    else:
        print("ERROR in getting token ", myResponse.status_code)
        myResponse2 = np.nan

    myResponse3 = requests.post(url3, auth=(email, password))

    responses = [myResponse, myResponse2, myResponse3]

    return df, responses


# %% DOWNLOAD & PREPARE DATA
userid_of_shared_user = input(
    "You acknowledge that this is exploratory (Press Return):\n"
)

if userid_of_shared_user in "":
    userid_of_shared_user = np.nan

weeks_of_data = np.int(input(
    "How many weeks of data do you want to analyze? (2-4 is recommended)\n"
))

date_data_pulled = dt.datetime.now().strftime("%Y-%d-%mT%H-%M")

data, responses = get_data_from_api(
    weeks_of_data=weeks_of_data,
    userid_of_shared_user=userid_of_shared_user
)

print(len(data), "rows of data have been downloaded")

if pd.isna(userid_of_shared_user):
    userID = responses[0].json()["userid"]
else:
    userID = userid_of_shared_user

metadata = pd.DataFrame(index=[userID])

# ADD UPLOAD DATE
data = add_uploadDateTime(data)

# round all data to the nearest 5 minutes
rounded_data = round_time(
    data,
    timeIntervalMinutes=5,
    timeField="time",
    roundedTimeFieldName="roundedTime",
    startWithFirstRecord=True,
    verbose=False
)

rounded_data["roundedTime"] = rounded_data["roundedTime"].apply(remove_timezone)
cgm_df = rounded_data.groupby(by="type").get_group("cbg").dropna(axis=1, how="all")
# get data in mg/dL units
cgm_df["mg_dL"] = mmolL_to_mgdL(cgm_df["value"]).astype(int)

cgm_df = cgm_df[["roundedTime", "mg_dL"]]
cgm_df.reset_index(drop=True, inplace=True)


# %% build join cgm snippets function

def get_cgm_snippets(
        df,
        time_field="roundedTime",
        time_interval_minutes=5,
        min_gap_size=15,
        min_snippet_minutes=75,
):
    '''
    Return array of snippet starts and sizes that meet input conditions.

    Parameters
    ----------
    df : pd.DataFrame
        Pandas dataframe that contains cgm data and a time field
    time_field : str
        Name of dataframe column that contains datetime information
    time_interval_minutes : int
        The time interval of delta of the cgm data, typically 5 minutes and sometimes 15
    min_gap_size : int
        This defines a gap, where a gap must be greater than min_gap_size. Default 15 minutes.
        TODO: make this explanation clearer
    min_snippet_minutes : int
        This defines the minimum length of a snippet in minutes. A cgm snippet must be
        greater than this threshold in order to be stitched together with another snippet.
        TODO: make this explanation clearer

    Returns
    -------
    np.array
        A two column array. The first column contains the index of the snippet starts,
        and the second column contains the size of each snippet.
    '''

    # make sure the time field is in the right form
    t = pd.to_datetime(df[time_field])

    # calculate the time between consecutive records
    t_shift = pd.to_datetime(df[time_field].shift(1))
    df["timeBetweenRecords"] = \
        round((t - t_shift).dt.days * (86400 / (60 * time_interval_minutes)) +
              (t - t_shift).dt.seconds / (60 * time_interval_minutes)) * time_interval_minutes

    # separate the data into chunks if timeBetweenRecords is greater than largest allowable gap
    snippet_index = list(
        df.query("abs(timeBetweenRecords) > " + str(min_gap_size)).index
    )
    snippet_index.insert(0, 0)

    # create a dataframe of just the snippet starts and sizes
    just_snippets = pd.DataFrame(snippet_index, columns=["snippet_index"])
    snippet_index.append(len(df))
    snippet_size = np.diff(snippet_index)
    just_snippets["snippet_size"] = snippet_size

    # get rid of all snippets less than (user defined length)
    keep_snippets_array = just_snippets.loc[
        just_snippets["snippet_size"] >= (min_snippet_minutes / time_interval_minutes),
        :
    ].values

    return keep_snippets_array

keep_snippets_array = get_cgm_snippets(df=cgm_df)

# %% blend snippets together using weighted sum
t_df = cgm_df.copy()
n_smoothing_points = int(min_snippet_minutes / time_interval_minutes)

snip_start = keep_snippets_array[0][0]
snip_end = snip_start + keep_snippets_array[0][1] - 1
s_size = keep_snippets_array[0][1]
previous_trace = t_df.loc[snip_start:snip_end, "mg_dL"].values
for s in range(1, len(keep_snippets_array)):
    snip_start = keep_snippets_array[s][0]
    snip_end = snip_start + keep_snippets_array[s][1] - 1
    s_size = keep_snippets_array[s][1]
    current_trace = t_df.loc[snip_start:snip_end, "mg_dL"].values

    # weight the last n_smoothing_points of the previous trace
    weighted_prev = previous_trace[-n_smoothing_points:] * np.linspace(1, 0, n_smoothing_points)
    # weight the first n_smoothing_points of the current trace
    weighted_curr = current_trace[:n_smoothing_points] * np.linspace(0, 1, n_smoothing_points)
    # combine the weighted traces to make a smooth transition
    overlap_trace = weighted_prev + weighted_curr
    # append the three traces together
    print(previous_trace, current_trace, overlap_trace)
    fig = px.line(y=overlap_trace, title="Combined Snippets")
    prev_trace = go.Scatter(y=previous_trace[-n_smoothing_points:], name="Left Snippet")
    fig.add_trace(prev_trace)
    curr_trace = go.Scatter(y=current_trace[:n_smoothing_points], name="Right Snippet")
    fig.add_trace(curr_trace)
    plot(fig)

    previous_trace = np.append(
        previous_trace[:-n_smoothing_points],
        np.append(
            overlap_trace,
            current_trace[n_smoothing_points:]
        )
    )



# for testing purposes, push this data back to the original so a plot can be made



# %% View original and joined (stitched) plots
fig = px.line(y=cgm_df["mg_dL"])
joined_trace = px.scatter(y=previous_trace)
fig.add_trace(joined_trace.data[0])
plot(fig)


# %% OLD STUFF
# # GET CGM DATA
# # group data by type
# groupedData = clean_data.groupby(by="type")
#
# # filter by cgm and sort by uploadTime
# cgmData = groupedData.get_group("cbg").dropna(axis=1, how="all")
#
# # get rid of duplicates that have the same ["deviceTime", "value"]
# cgmData, nCgmDuplicatesRemovedDeviceTime = removeCgmDuplicates(cgmData, "deviceTime")
# metadata["nCgmDuplicatesRemovedDeviceTime"] = nCgmDuplicatesRemovedDeviceTime
#
# # get rid of duplicates that have the same ["time", "value"]
# cgmData, nCgmDuplicatesRemovedUtcTime = removeCgmDuplicates(cgmData, "time")
# metadata["cnCgmDuplicatesRemovedUtcTime"] = nCgmDuplicatesRemovedUtcTime
#
# # get rid of duplicates that have the same "roundedTime"
# cgmData, nCgmDuplicatesRemovedRoundedTime = removeDuplicates(cgmData, "roundedTime")
# metadata["nCgmDuplicatesRemovedRoundedTime"] = nCgmDuplicatesRemovedRoundedTime
#
# # get start and end times
# cgmBeginDate, cgmEndDate = getStartAndEndTimes(cgmData, "roundedTime")
# metadata["cgm.beginDate"] = cgmBeginDate
# metadata["cgm.endDate"] = cgmEndDate
#
# # create a contiguous time series
# rng = pd.date_range(cgmBeginDate, cgmEndDate, freq="5min")
# contiguousData = pd.DataFrame(rng, columns=["cDateTime"])
#
# # get data in mg/dL units
# cgmData["mg_dL"] = mmolL_to_mgdL(cgmData["value"]).astype(int)
#
# # merge data
# contig_cgm = pd.merge(
#     contiguousData,
#     cgmData[["roundedTime", "mg_dL"]],
#     left_on="cDateTime",
#     right_on="roundedTime",
#     how="left"
# )