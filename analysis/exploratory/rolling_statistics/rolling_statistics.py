#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: Process rolling statistics for Tidepool blood glucose 
             and insulin pump data.
version: 0.0.1
Created: 8/1/2018
author: Jason Meno
dependencies:
    * requires Tidepool user's datawith est.localTime
license: BSD-2-Clause

TODO:
    
"""

# %% Import Libraries
import pandas as pd
import numpy as np
from math import exp,pow
import datetime as dt
import os
import sys
import argparse
import json
import time
import matplotlib.pyplot as plt
import plotly.plotly as py
from plotly import tools
import plotly.graph_objs as go
from plotly.offline import download_plotlyjs, init_notebook_mode, plot, iplot
import cufflinks as cf

# %% Function Definitions
def classify_data(filename):
    
    cgm_bool = False
    class_type = "NA"
    
    file_loc = os.path.join(data_folder,filename+".csv")
    
    # Read the first line of file
    with open(file_loc, 'r') as f:
        header = f.readline()
        
    if "value" in header:
        cgm_bool = True
        class_type = "CGM"
    if "normal" in header:
        if cgm_bool:
            class_type = "MIXED"
        else:
            class_type = "PUMP"
            
    return class_type

    
def read_data(filename, class_type):
    
    cgm_data = []
    bolus_data = []
    basal_data = []
    
    file_loc = os.path.join(data_folder,filename+".csv")
    
    if class_type == "MIXED":
        #Both CGM & Pump data
        col_names = ['carbInput',
                     'deviceTime',
                     'id',
                     'time',
                     'bolus',
                     'type',
                     'uploadId',
                     'value',
                     'est.type',
                     'est.localTime',
                     'normal',
                     'rate',
                     'duration'
                     ] 
        
        df = pd.read_csv(file_loc, usecols=col_names, low_memory=False)
        
        #Removing "UNCERTAIN" est.type (since no est.localTime is evaluated)
        df = df[df["est.type"]!="UNCERTAIN"].copy()
        
        cgm_data = df[df["type"] == "cbg"].copy()
        bolus_data = df[df["type"] == "bolus"].copy()
        basal_data = df[df["type"] == "basal"].copy()
        upload_data = df[df["type"] == "upload"].copy()
        
    elif class_type == "PUMP":
        #Pump data only
        col_names = ['carbInput',
                     'deviceTime',
                     'id',
                     'time',
                     'type',
                     'uploadId',
                     'est.type',
                     'est.localTime',
                     'normal',
                     'rate',
                     'duration'
                     ] 
       
        df = pd.read_csv(file_loc, usecols=col_names, low_memory=False)
        
        #Removing "UNCERTAIN" est.type (since no est.localTime is evaluated)
        df = df[df["est.type"]!="UNCERTAIN"].copy()
        
        bolus_data = df[df["type"] == "bolus"].copy()
        basal_data = df[df["type"] == "basal"].copy()
        upload_data = df[df["type"] == "upload"].copy()
        
    else:
        #CGM data only
        col_names = ['deviceTime',
                     'id',
                     'type',
                     'time',
                     'uploadId',
                     'value',
                     'est.type',
                     'est.localTime',
                     ]  

        df = pd.read_csv(file_loc, usecols=col_names, low_memory=False)
        
        #Removing "UNCERTAIN" est.type (since no est.localTime is evaluated)
        df = df[df["est.type"]!="UNCERTAIN"].copy()
       
        cgm_data = df[df["type"] == "cbg"].copy()
        upload_data = df[df["type"] == "upload"].copy()
    
    
    first_date = df["est.localTime"].min()
    last_date = df["est.localTime"].max()
    
    return cgm_data, bolus_data, basal_data, upload_data, first_date, last_date

def remove_duplicates(df, upload_data):
  
    #Sort uploads by oldest uploads first
    upload_data = upload_data.sort_values(ascending=True, by="est.localTime")
    
    #Create an ordered dictionary (i.e. uploadId1 = 1, ,uploadId2 = 2, etc)
    upload_order_dict = dict(
                        zip(upload_data["uploadId"],
                        list(range(1,1+len(upload_data.uploadId.unique()
                            )))))
    

    #Sort data by upload order from the ordered dictionary
    df["upload_order"] = df["uploadId"]
    df["upload_order"] = df["upload_order"].map(upload_order_dict)
    df = df.sort_values(ascending=True, by="upload_order")
    
    #Replace any healthkit data deviceTimes (NaN) with a unique id
    #This prevents healthkit data with blank deviceTimes from being removed
    df.deviceTime.fillna(df.id,inplace=True)
    
    #Drop duplicates using est.localTime+value, time(utc time)+value, 
    # deviceTime+value, and est.localTime alone
    #The last entry is kept, which contains the most recent upload data
    values_before_removal = len(df.value)
    df = df.drop_duplicates(subset=["est.localTime","value"], keep="last")
    df = df.drop_duplicates(subset=["time","value"], keep="last")
    df = df.drop_duplicates(subset=["deviceTime","value"], keep="last")
    df = df.drop_duplicates(subset=["est.localTime"], keep="last")
    values_after_removal = len(df.value)
    duplicates_removed = values_before_removal-values_after_removal
    
    #Re-sort the data by est.localTime
    df = df.sort_values(ascending=True, by="est.localTime")
    
    return df, duplicates_removed

def remove_rounded_duplicates(df,data_type):
    new_df = df.copy()
    values_before_removal = len(new_df["est.localTime_rounded"])
    
    if(data_type == "cgm"):
        new_df = new_df.drop_duplicates(subset=["est.localTime_rounded"], keep="last")
        
        #Convert to mg_dL before merging 
        #(casting to type int will not work with NaNs later)
        #df = df.rename(columns={"value":"mmol_L"})
        
        new_df["mg_dL"] = (new_df.value*18.01559).astype(int)
        
        #df["mmol_L"] = df.value.copy()
        #df["value"] = df["mg_dL"].copy()
    
    elif(data_type == "bolus"):
        
        new_df["normal"] = new_df.groupby(by="est.localTime_rounded")["normal"].transform('sum')
        new_df = new_df.drop_duplicates(subset=["est.localTime_rounded"], keep="last")
        
    else:
        new_df = new_df.drop_duplicates(subset=["est.localTime_rounded"], keep="last")
        




    values_after_removal = len(new_df["est.localTime_rounded"])
    duplicates_removed = values_before_removal-values_after_removal
    
    return new_df, duplicates_removed
   
def fill_basal_gaps(df):
    #Old Forward Filling Method
    #df["rate"].fillna(method='ffill', inplace=True)
    
    #Fill basal by given duration
    for dur in range(0,len(df.duration)):
        if(~np.isnan(df.duration.iloc[dur])):
            df.rate.iloc[dur:(dur+int(round(df.duration.iloc[dur]/1000/60/5)))].fillna(method='ffill',inplace=True)
    
    return df
    
def round5Minutes(df):

    # sort ascendingly by est.localTime
    df.sort_values(by="est.localTime", ascending=True, inplace=True)
    df.reset_index(drop=True, inplace=True)

    # calculate the time-in-between (TIB) consecutive records
    t = pd.to_datetime(df["est.localTime"])
    t_shift = pd.to_datetime(df["est.localTime"].shift(1))
    df["TIB"] = round((t - t_shift).dt.days*(86400/300) +
                      (t - t_shift).dt.seconds/300) * 5

    # separate the data into chunks if TIB is greater than 5 minutes
    largeGaps = list(df.query("TIB > 5").index)
    largeGaps.insert(0,0)
    largeGaps.append(len(df))

    # loop through each chunk to get the cumulative sum and the rounded time
    for gIndex in range(0, len(largeGaps) - 1):

        df.loc[largeGaps[gIndex], "TIB"] = 0

        df.loc[largeGaps[gIndex]:(largeGaps[gIndex + 1] - 1), "TIB_cumsum"] = \
            df.loc[largeGaps[gIndex]:(largeGaps[gIndex + 1] - 1), "TIB"].cumsum()

        df.loc[largeGaps[gIndex]:(largeGaps[gIndex + 1] - 1), "est.localTime_rounded"] = \
            pd.to_datetime(df.loc[largeGaps[gIndex], "est.localTime"]).round("5min") + \
            pd.to_timedelta(df.loc[largeGaps[gIndex]:(largeGaps[gIndex + 1] - 1), "TIB_cumsum"], unit="m")

    # sort descendingly by time
    df.sort_values(by="est.localTime_rounded", ascending=False, inplace=True)
    df.reset_index(drop=True, inplace=True)

    return df

    
def fill_time_gaps(df,first_date,last_date,data_type):
    first_date = pd.to_datetime(dt.datetime.fromtimestamp(pd.to_datetime(first_date).timestamp()+.000001)).round("30S")
    first_date = pd.to_datetime(dt.datetime.fromtimestamp(pd.to_datetime(first_date).timestamp()+.000001)).round("5min")
    
    last_date = pd.to_datetime(dt.datetime.fromtimestamp(pd.to_datetime(last_date).timestamp()+.000001)).round("30S")
    last_date = pd.to_datetime(dt.datetime.fromtimestamp(pd.to_datetime(last_date).timestamp()+.000001)).round("5min")
    #Create 5-min continuous time series in a new dataframe
    five_min_ts = pd.date_range(first_date, last_date, freq="5min")
    new_df = pd.DataFrame({"est.localTime_rounded":five_min_ts})
    
    # round est.localTime to nearest 30 seconds, then 5 minutes
    
    #df = round5Minutes(df)
    
    df["est.localTime_rounded"] = pd.to_datetime(pd.to_datetime(df["est.localTime"]).astype(np.int64)+1000).dt.round("30S")
    
    df["est.localTime_rounded"] = pd.to_datetime(pd.to_datetime(df["est.localTime_rounded"]).astype(np.int64)+1000).dt.round("5min")
    
  
    df, rounded_duplicates = remove_rounded_duplicates(df.copy(),data_type)    
    
   
    new_df = pd.merge(new_df,df,on="est.localTime_rounded",how="outer",indicator=True)
    
    #If basal data, forward fill the rates by duration into the NaNs
    if(data_type == "basal"):
        fill_basal_gaps(new_df)
        #new_df["rate"].fillna(method='ffill', inplace=True)
    #Duplicate checking
    #duplicates = new_df.loc[new_df["est.localTime"].duplicated(keep=False),:]
    return new_df, rounded_duplicates

def get_cgm_stats(df):
    
    #Generic Form
    #a.rolling(3,min_periods=3).apply(test_sum)
    #for index in range(2,len(df["est.localTime_rounded"])):
   
    #Set up specialized rolling sub-functions to use
    def get_perc_below(tmp, threshold):
        total_below = np.sum(tmp<threshold)
        perc_below = total_below / np.count_nonzero(~np.isnan(tmp))
        return perc_below
    
    def get_perc_above(tmp, threshold):
        total_above = np.sum(tmp>threshold)
        perc_above = total_above / np.count_nonzero(~np.isnan(tmp))
        return perc_above
    
    def get_perc_between(tmp, threshold1, threshold2):
        total_between = np.sum((tmp >= threshold1) & (tmp <= threshold2))
        perc_between = total_between / np.count_nonzero(~np.isnan(tmp))
        return perc_between
    
    def get_distance_traveled(tmp):
        distance = np.abs(np.diff(tmp)).sum()
        return distance
        
   # rolling_prefixes = ["15min","1hr","2hr","6hr","8hr","12hr","24hr",
    #                    "7day","14day","30day","90day","1year"]
    
    rolling_prefixes = ["24hr","7day","14day","30day","90day","1year"]
    
    #Set number of points per rolling window
    #rolling_points = [3,12,24,72,96,144,288,2016,4032,8640,25920,105120]
    rolling_points = [288,2016,4032,8640,25920,105120]
    #Set minimum percentage of points required to calculate rolling statistic
    percent_points = 0.7
    rolling_min = np.floor(percent_points*pd.DataFrame(rolling_points)).astype(int)
    
    #Loop through rolling stats for each time prefix
    for i in range(0,len(rolling_prefixes)):
        start_time = time.time()
        print("Mean")
        df[rolling_prefixes[i]+"_cgm_mean"] = df.mg_dL.rolling(rolling_points[i],
                                          min_periods=rolling_min.loc[i,0]).mean()
        
        # get estimated HbA1c or Glucose Management Index (GMI)
        # GMI(%) = 3.31 + 0.02392 x [mean glucose in mg/dL]
        # https://www.jaeb.org/gmi/
        print("A1C")
        df[rolling_prefixes[i]+"_cgm_a1c"] = 3.31 + (0.02392*df[rolling_prefixes[i]+"_cgm_mean"])
        
        print("Stddev")
        df[rolling_prefixes[i]+"_cgm_stddev"] = df.mg_dL.rolling(rolling_points[i],
                                          min_periods=rolling_min.loc[i,0]).std()
        
        print("Cov")
        df[rolling_prefixes[i]+"_cgm_cov"] = df[rolling_prefixes[i]+"_cgm_stddev"]/df[rolling_prefixes[i]+"_cgm_mean"]
        
        print("Traveled")
        df[rolling_prefixes[i]+"_cgm_traveled"] = df.mg_dL.rolling(rolling_points[i],
                                          min_periods=rolling_min.loc[i,0]).apply(func=get_distance_traveled)
        
        print("<54")
        df[rolling_prefixes[i]+"_cgm_percentBelow54"] = df.mg_dL.rolling(rolling_points[i],
                                          min_periods=rolling_min.loc[i,0]).apply(func=get_perc_below,args=[54])
        print("<70")
        df[rolling_prefixes[i]+"_cgm_percentBelow70"] = df.mg_dL.rolling(rolling_points[i],
                                          min_periods=rolling_min.loc[i,0]).apply(func=get_perc_below,args=[70])
        print("TIR")
        df[rolling_prefixes[i]+"_cgm_percentTimeInRange"] = df.mg_dL.rolling(rolling_points[i],
                                          min_periods=rolling_min.loc[i,0]).apply(func=get_perc_between,args=[70,180])
        print(">180")
        df[rolling_prefixes[i]+"_cgm_percentAbove180"] = df.mg_dL.rolling(rolling_points[i],
                                          min_periods=rolling_min.loc[i,0]).apply(func=get_perc_above,args=[180])
        print(">250")
        df[rolling_prefixes[i]+"_cgm_percentAbove250"] = df.mg_dL.rolling(rolling_points[i],
                                          min_periods=rolling_min.loc[i,0]).apply(func=get_perc_above,args=[250])
        print("min")
        df[rolling_prefixes[i]+"_cgm_min"] = df.mg_dL.rolling(rolling_points[i],
                                          min_periods=rolling_min.loc[i,0]).min()
        print("Q10")
        df[rolling_prefixes[i]+"_cgm_Q10"] = df.mg_dL.rolling(rolling_points[i],
                                          min_periods=rolling_min.loc[i,0]).quantile(0.10)
        print("Q25")
        df[rolling_prefixes[i]+"_cgm_Q25"] = df.mg_dL.rolling(rolling_points[i],
                                          min_periods=rolling_min.loc[i,0]).quantile(0.25)
        print("median")
        df[rolling_prefixes[i]+"_cgm_median"] = df.mg_dL.rolling(rolling_points[i],
                                          min_periods=rolling_min.loc[i,0]).quantile(0.50)
        print("Q75")
        df[rolling_prefixes[i]+"_cgm_Q75"] = df.mg_dL.rolling(rolling_points[i],
                                          min_periods=rolling_min.loc[i,0]).quantile(0.75)
        print("Q90")
        df[rolling_prefixes[i]+"_cgm_Q90"] = df.mg_dL.rolling(rolling_points[i],
                                          min_periods=rolling_min.loc[i,0]).quantile(0.90)
        print("max")
        df[rolling_prefixes[i]+"_cgm_max"] = df.mg_dL.rolling(rolling_points[i],
                                          min_periods=rolling_min.loc[i,0]).max()
        
        print(rolling_prefixes[i], ' took {0} seconds.'.format(time.time() - start_time))
    return df

def get_bolus_stats(df):
    
    #Generic Form
    #a.rolling(3,min_periods=3).apply(test_sum)
    #for index in range(2,len(df["est.localTime_rounded"])):
        
   # rolling_prefixes = ["15min","1hr","2hr","6hr","8hr","12hr","24hr",
    #                    "7day","14day","30day","90day","1year"]
    
    rolling_prefixes = ["24hr","7day","14day","30day","90day","1year"]
    
    #Set number of points per rolling window
    #rolling_points = [3,12,24,72,96,144,288,2016,4032,8640,25920,105120]
    rolling_points = [288,2016,4032,8640,25920,105120]
    
    #Loop through rolling stats for each time prefix
    for i in range(0,len(rolling_prefixes)):
        start_time = time.time()
        print("Mean")
        df[rolling_prefixes[i]+"_bolus_mean"] = df.normal.rolling(rolling_points[i],min_periods=1).mean()
        
        print("Stddev")
        df[rolling_prefixes[i]+"_bolus_stddev"] = df.normal.rolling(rolling_points[i],min_periods=1).std()
        
        print("Cov")
        df[rolling_prefixes[i]+"_bolus_cov"] = df[rolling_prefixes[i]+"_bolus_stddev"]/df[rolling_prefixes[i]+"_bolus_mean"]
        
        print("Total")
        df[rolling_prefixes[i]+"_bolus_total"] = df.normal.rolling(rolling_points[i],min_periods=1).sum()
        
        print("min")
        df[rolling_prefixes[i]+"_bolus_min"] = df.normal.rolling(rolling_points[i],min_periods=1).min()
        print("Q10")
        df[rolling_prefixes[i]+"_bolus_Q10"] = df.normal.rolling(rolling_points[i],min_periods=1).quantile(0.10)
        print("Q25")
        df[rolling_prefixes[i]+"_bolus_Q25"] = df.normal.rolling(rolling_points[i],min_periods=1).quantile(0.25)
        print("median")
        df[rolling_prefixes[i]+"_bolus_median"] = df.normal.rolling(rolling_points[i],min_periods=1).quantile(0.50)
        print("Q75")
        df[rolling_prefixes[i]+"_bolus_Q75"] = df.normal.rolling(rolling_points[i],min_periods=1).quantile(0.75)
        print("Q90")
        df[rolling_prefixes[i]+"_bolus_Q90"] = df.normal.rolling(rolling_points[i],min_periods=1).quantile(0.90)
        print("max")
        df[rolling_prefixes[i]+"_bolus_max"] = df.normal.rolling(rolling_points[i],min_periods=1).max()
        
        print(rolling_prefixes[i], ' took {0} seconds.'.format(time.time() - start_time))
    return df  

def get_basal_stats(df):
    
    #Generic Form
    #a.rolling(3,min_periods=3).apply(test_sum)
    #for index in range(2,len(df["est.localTime_rounded"])):
        
   # rolling_prefixes = ["15min","1hr","2hr","6hr","8hr","12hr","24hr",
    #                    "7day","14day","30day","90day","1year"]
    
    rolling_prefixes = ["24hr","7day","14day","30day","90day","1year"]
    
    #Set number of points per rolling window
    #rolling_points = [3,12,24,72,96,144,288,2016,4032,8640,25920,105120]
    rolling_points = [288,2016,4032,8640,25920,105120]
    
    #Loop through rolling stats for each time prefix
    for i in range(0,len(rolling_prefixes)):
        start_time = time.time()
        print("Mean")
        df[rolling_prefixes[i]+"_basal_mean"] = df.rate.rolling(rolling_points[i],min_periods=1).mean()
        
        print("Stddev")
        df[rolling_prefixes[i]+"_basal_stddev"] = df.rate.rolling(rolling_points[i],min_periods=1).std()
        
        print("Cov")
        df[rolling_prefixes[i]+"_basal_cov"] = df[rolling_prefixes[i]+"_basal_stddev"]/df[rolling_prefixes[i]+"_basal_mean"]
        
        print("Total")
        df[rolling_prefixes[i]+"_basal_total"] = df.rate.rolling(rolling_points[i],min_periods=1).sum()
        
        print("min")
        df[rolling_prefixes[i]+"_basal_min"] = df.rate.rolling(rolling_points[i],min_periods=1).min()
        print("Q10")
        df[rolling_prefixes[i]+"_basal_Q10"] = df.rate.rolling(rolling_points[i],min_periods=1).quantile(0.10)
        print("Q25")
        df[rolling_prefixes[i]+"_basal_Q25"] = df.rate.rolling(rolling_points[i],min_periods=1).quantile(0.25)
        print("median")
        df[rolling_prefixes[i]+"_basal_median"] = df.rate.rolling(rolling_points[i],min_periods=1).quantile(0.50)
        print("Q75")
        df[rolling_prefixes[i]+"_basal_Q75"] = df.rate.rolling(rolling_points[i],min_periods=1).quantile(0.75)
        print("Q90")
        df[rolling_prefixes[i]+"_basal_Q90"] = df.rate.rolling(rolling_points[i],min_periods=1).quantile(0.90)
        print("max")
        df[rolling_prefixes[i]+"_basal_max"] = df.rate.rolling(rolling_points[i],min_periods=1).max()
        
        print(rolling_prefixes[i], ' took {0} seconds.'.format(time.time() - start_time))
    return df   

#Calculate the running insulin on board with basal and bolus data
def get_insulin_on_board(bolus_data,basal_data):
    
    # params
    td = float(6*60) # duration
    tp = float(75) # activity peak
    
    #Exponential model from Loop
    #See https://github.com/ps2/LoopIOB/blob/master/ScalableExp.ipynb
    def scalable_exp_iob(t, tp, td):
        tau = tp*(1-tp/td)/(1-2*tp/td)
        a = 2*tau/td
        S = 1/(1-a+(1+a)*exp(-td/tau))
        return 1-S*(1-a)*((pow(t,2)/(tau*td*(1-a)) - t/tau - 1)*exp(-t/tau)+1)
    
    x = np.linspace(0,int(td),num=int(td/5))
    model_curve = np.array([scalable_exp_iob(t, tp=tp, td=td) for t in x])
    model_length = len(model_curve)
    
    
    iob_data = bolus_data[["est.localTime_rounded","normal"]].copy()
    iob_data["rate"] = basal_data.rate.copy()
    
    iob_data["iob"] = 0
    
    #Calculate Bolus Curves for IOB
    for dur in range(0,len(iob_data.normal)-model_length):
        if(~np.isnan(iob_data.normal.iloc[dur])):
            iob_data.loc[dur:(dur+model_length-1),"iob"] = iob_data.loc[dur:(dur+model_length-1),"iob"] + model_curve*iob_data.normal[dur]
     
    #Calculate Basal Curves for IOB (TOO LONG TO CALCULATE!!)
    #for dur in range(0,len(iob_data.rate)-model_length):
    #    if(~np.isnan(iob_data.rate.iloc[dur])):
    #        print("Basal IOB:", dur)
    #        iob_data.loc[dur:(dur+model_length-1),"iob"] = iob_data.loc[dur:(dur+model_length-1),"iob"] + model_curve*(iob_data.rate[dur]/12)
    
    iob_data["iob"].replace(0,np.NaN,inplace=True)
    
    return iob_data

def filter_stats(df,filter_type):
    
    new_df = df.copy()
    new_df.set_index("est.localTime_rounded",inplace=True)
    
    if(filter_type == "daily"):
        new_df = new_df.at_time('5:00')
        new_df.index = new_df.index-dt.timedelta(hours=6)
        
    elif(filter_type == "weekdays"):
        print("Weekdays script")
    elif(filter_type == "24hr"):
        print("24 hour script")
    else:
        print("No filter type selected (daily/weekdays/24hr)")

    return new_df        
# %% Main Script    
csv_name = "CSV_FILENAME"
data_folder = os.path.join(os.getcwd(),"CSV_DATA_PATH")
donor_class = classify_data(csv_name)
cgm_df, bolus_df, basal_df, upload_df, first_ts, last_ts = \
                                read_data(csv_name, donor_class)

#Class processing
if(donor_class == "MIXED"):
    
    #Remove Duplicates
    cgm_df, cgm_duplicate_count = \
                    remove_duplicates(cgm_df, upload_df)
    bolus_df, bolus_duplicate_count = \
                    remove_duplicates(bolus_df, upload_df)
    basal_df, basal_duplicate_count = \
                    remove_duplicates(basal_df, upload_df)
    
    #Fill in time-series gaps
    cgm_df, cgm_rounded_duplicate_count = \
        fill_time_gaps(cgm_df,first_ts,last_ts,"cgm")
    bolus_df, bolus_rounded_duplicate_count = \
        fill_time_gaps(bolus_df,first_ts,last_ts,"bolus")
    basal_df, basal_rounded_duplicate_count = \
        fill_time_gaps(basal_df,first_ts,last_ts,"basal")
    
    #Get Rolling Statistics    
    cgm_df = get_cgm_stats(cgm_df)
    bolus_df = get_bolus_stats(bolus_df)
    basal_df = get_basal_stats(basal_df)
    
    #Get insulin on board
    iob_df = get_insulin_on_board(bolus_df,basal_df)
    
    #Filter Rolling Stats - Continuous Daily (5am-5am)
    cgm_daily = filter_stats(cgm_df, 'daily')
    bolus_daily = filter_stats(bolus_df, 'daily')
    basal_daily = filter_stats(basal_df, 'daily')
    
    #Filter Rolling Stats - By Weekday (Sunday-Saturday)
    #cgm_weekday = filter_stats(cgm_df, 'weekdays')
    #bolus_weekday = filter_stats(bolus_df, 'weekdays')
    #basal_weekday = filter_stats(basal_df, 'weekdays')
    
    #Filter Rolling Stats - Static 24-hour Classic Summary
    #cgm_24hr = filter_stats(cgm_df, '24hr')
    #bolus_24hr = filter_stats(bolus_df, '24hr')
    #basal_24hr = filter_stats(basal_df, '24hr')
   
elif(donor_class == "PUMP"):
    bolus_df, bolus_duplicate_count = \
                    remove_duplicates(bolus_df, upload_df)
    basal_df, basal_duplicate_count = \
                    remove_duplicates(basal_df, upload_df)
                    
    bolus_df, bolus_rounded_duplicate_count = \
        fill_time_gaps(bolus_df,first_ts,last_ts,"bolus")
    basal_df, basal_rounded_duplicate_count = \
        fill_time_gaps(basal_df,first_ts,last_ts,"basal")
        
    #Get Rolling Statistics    
    bolus_df = get_bolus_stats(bolus_df)
    basal_df = get_basal_stats(basal_df)
    
else:
    cgm_df, cgm_duplicate_count = \
                    remove_duplicates(cgm_df, upload_df)
        
    cgm_df, cgm_rounded_duplicate_count = \
        fill_time_gaps(cgm_df,first_ts,last_ts,"cgm")
      
    #Get Rolling Statistics    
    cgm_df = get_cgm_stats(cgm_df)