#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 22 06:46:33 2019

@author: ed
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: visualize users settings and events
version: 0.0.1
created: 2019-01-11
author: Ed Nykaza
dependencies:
    *
license: BSD-2-Clause
"""


# %% REQUIRED LIBRARIES
import pandas as pd
import numpy as np
from pytz import timezone
from datetime import timedelta
import datetime as dt
import os
import argparse
import pdb
import matplotlib.pyplot as plt
import plotly
import plotly.plotly as py
import plotly.graph_objs as go
from plotly.offline import download_plotlyjs, init_notebook_mode, plot, iplot
import plotly.io as pio


# %% FUNCTIONS
def make_bold(val_list):
    bold_list = []
    for val in val_list:
        bold_list.append('<b>' + str(val) + '</b>')
    return bold_list

def make_bold_and_round(val_list, nDecimalPlaces):
    bold_list = []
    for val in val_list:
        if nDecimalPlaces == 0:
            bold_list.append('<b>' + str(int(np.round(val, nDecimalPlaces))) + '</b>')

        else:
            bold_list.append('<b>' + str(np.round(val, nDecimalPlaces)) + '</b>')
    return bold_list


def save_fig(fig, plot_name, width, height, scale):
    pio.write_image(
    fig,
    os.path.join(
        figure_path,
        plot_name + ".png"
    ),
    width=width,
    height=height,
    scale=scale)

    return


def make_static_plot(field, yLabel, figName, df, yMin, yMax):

    df.sort_values("categories", inplace=True)

    traces = []
    for yd in df.categories.unique():
        traces.append(go.Box(
            y=df.loc[df["categories"] == yd, field].values,
            x=df.loc[df["categories"] == yd, "categories"].values,
            name=yd,
            boxpoints="all",
            notched=True,
            hoverlabel=dict(font=dict(size=22)),
            marker=dict(
                color=df.loc[df["categories"] == yd, "allColors"].describe()["top"],
                opacity=0,
            ),
        ))

    layout = go.Layout(
        font=dict(
            size=22
        ),
        xaxis=dict(
            tickangle=52.5
        ),
        yaxis=dict(
            title=yLabel,
            range=[yMin, yMax],
            showgrid=True,
            gridcolor='#f1f3f4',
            gridwidth=2,
            zeroline=True,
            zerolinecolor='#f1f3f4',
            zerolinewidth=2,
        ),
        margin=dict(
            l=100,
            r=200,
            b=250,
            t=50,
        ),

        boxmode='group',
        showlegend=False,
        legend=dict(font=dict(size=14))
    )

    fig = go.Figure(data=traces, layout=layout)

    save_fig(fig, figName + "-boxplot-lowRes", 1800, 1200, 1)
    save_fig(fig, figName + "-boxplot-highRes", 1800, 1200, 4)

def make_static_table(field, figName, filteredDF, nDecimals, return_summaryTable=False):

    # first make an overall table
    allCounts = filteredDF.groupby(["hashID"])[field].describe()
    allAgeTable = pd.DataFrame(index=[field])
    allAgeTable["min"] = allCounts["min"].min()
    allAgeTable["max"] = allCounts["max"].max()
    allAgeTable["U"] = len(allCounts)
    allAgeTable["N"] = allCounts["count"].sum()

    # then make summary per categories
    uniqueCounts = filteredDF.groupby(["categories"])["hashID"].describe()
    uniqueCounts.reset_index(inplace=True)
    summaryTable = filteredDF.groupby("categories")[field].describe()
    summaryTable.reset_index(inplace=True)
    summaryTable = pd.merge(summaryTable, uniqueCounts[["categories", "unique"]], how="left", on="categories")
    summaryTable = pd.merge(summaryTable, catColorDF, how="left", on="categories")
    summaryTable["unique"] = summaryTable["unique"].astype(float)

    # add in interquartile range
    summaryTable["IQR"] = summaryTable["75%"] - summaryTable["25%"]

    col_headings = make_bold(["Group", "N", "U", "Average", "Stdev", "Min", "Q1", "Median", "Q3", "Max"])

    trace = go.Table(
        header=dict(values=col_headings,
                    fill = dict(color='white'),
                    align = ['center', 'center', 'center'],
                    font = dict(color = 'black', size=12)),
        columnwidth=[1.5, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        cells=dict(values=[make_bold(summaryTable["categories"]),
                           make_bold_and_round(summaryTable["count"], 0),
                           make_bold_and_round(summaryTable["unique"], 0),
                           make_bold_and_round(summaryTable["mean"], nDecimals),
                           make_bold_and_round(summaryTable["std"], nDecimals),
                           make_bold_and_round(summaryTable["min"], nDecimals),
                           make_bold_and_round(summaryTable["25%"], nDecimals),
                           make_bold_and_round(summaryTable["50%"], nDecimals),
                           make_bold_and_round(summaryTable["75%"], nDecimals),
                           make_bold_and_round(summaryTable["max"], nDecimals)],
                   fill = dict(color = [summaryTable["allColors"]]),
                   align = ['center', 'center', 'center'],
                   font = dict(color = 'black', size=10),
                   height = 20)
        )

    fig = go.Figure()
    fig.add_trace(trace)

    pio.write_image(
        fig,
        os.path.join(
            figure_path,
            figName + "-table-highRes.png"
        ),
        width=1200,
        height=1200,
        scale=4)

    pio.write_image(
        fig,
        os.path.join(
            figure_path,
            figName + "-table-lowRes.png"
        ),
        width=1200,
        height=1200,
        scale=1)

    summaryTable.to_csv(
        os.path.join(
            figure_path,
            figName + "-table.csv"
        )
    )
    allAgeTable.to_csv(
        os.path.join(
            figure_path,
            figName + "-all-age-table.csv"
        )
    )

    if return_summaryTable:
        return summaryTable, allAgeTable
    else:
        return


def make_lite_interactive_boxplot(field, yLabel, df, yMin, yMax):
    df.sort_values("categories", inplace=True)

    traces = []
    for yd in df.categories.unique():
        yValues = df.loc[df["categories"] == yd, field]
        yStats = yValues.describe()
        yMinimum = yStats["min"]
        yQ1 = yStats["25%"]
        yQ2 = yStats["50%"]
        yQ3 = yStats["75%"]
        yMaximum = yStats["max"]
        yIQR = yQ3 - yQ1
        maxWhisker = yIQR * 1.5
        lowWhiskerBound = yQ1 - maxWhisker
        highWhiskerBound = yQ3 + maxWhisker
        yLowerFence = yValues[yValues >= lowWhiskerBound].min()
        yUpperFence = yValues[yValues <= highWhiskerBound].max()
        yBoxData = [yMinimum, yLowerFence, yQ1, yQ1, yQ1, yQ1, yQ1,
                    yQ2, yQ3, yQ3, yQ3, yQ3, yQ3,
                    yUpperFence, yMaximum]

        # get N and U
        nDays = df.loc[df["categories"] == yd, "count"].median().astype(int)
        uniqueDonors = df.loc[df["categories"] == yd, "unique"].median().astype(int)

        traces.append(go.Box(
            y=yBoxData,
            jitter=0,
            pointpos=0,
            text=list(np.repeat("N=%s, U=%s" % (nDays, uniqueDonors), len(yBoxData))),
            hoverinfo="y+text",
            name=yd,
            boxpoints="all",
            notched=False,
            marker=dict(
                color=df.loc[df["categories"] == yd, "allColors"].describe()["top"],
                opacity=0,
            ),
        ))

    layout = go.Layout(
        yaxis=dict(
            title=yLabel,
            range=[yMin, yMax],
            showgrid=True,
            gridcolor='#f1f3f4',
            gridwidth=2,
            zeroline=True,
            zerolinecolor='#f1f3f4',
            zerolinewidth=2,
        ),
        showlegend=True
    )

    fig = go.Figure(data=traces, layout=layout)
    plot_url = py.plot(fig, filename="Distribution of " + figName, auto_open=False)
    print(figName, plot_url)

    return


def filter_data(df, min_days_criteria=7):

    # keep all type1 adn null diagnosis data (not specified)
    df = df[((df.diagnosisType.isnull()) | (df.diagnosisType == "type1"))]

    # filter out invalid ages and ylw
    df = df[((df.age.astype(float) >= 0) & (df.age.astype(float) <= 90))]
    df = df[((df.ylw.astype(float) >= 0) & (df.ylw.astype(float) <= 80))]

    # filter out invalid pump and cgm days
    df = df[((df["validPumpData"]) & (df["validCGMData"]))]

    # filter out Paradigm Veo Pumps
    df = df[~df["pump.top"].str.contains("Paradigm Veo")]

    # filter out omnipod with mg/dL likely settings
    df = df[~((df["pump.top"].str.contains("InsOmn-130")) &
              (df['pumpSettings.isfLikelyUnits'] == "mg/dL"))]

    # require a minimum number of days of data
    dayGroups = pd.DataFrame(df.groupby(["hashID", "age", "ylw"]).day.count()).reset_index()
    dayGroups.rename(columns={"day": "nDays"}, inplace=True)
    df = pd.merge(df, dayGroups, how="left", on=["hashID", "age", "ylw"])

    df = df[df["nDays"] >= min_days_criteria]

    return df


def merge_dayData(df, dayDF):

    df = pd.merge(
        df,
        dayDF[[
            "hashID",
            "day",
            "validPumpData",
            "atLeast3Boluses",
            "validCGMData",
            "diagnosisType",
            "pump.top",
            "pumpSettings.isfLikelyUnits"
        ]],
        how="left",
        on=["hashID", "day"]
    )

    return df


def bin_data(df, ageBins, ageGroupNames, ylwBins, ylwGroupNames, catColorDF, min_unique_donors=10):

    # bin data (defined above)
    df["ageBins"] = pd.cut(df["age"], ageBins, labels=ageGroupNames)
    df["ylwBins"] = pd.cut(df["ylw"], ylwBins, labels=ylwGroupNames)
    df["ageCategories"] = df["ageBins"].astype(str)
    df["ylwCategories"] = df["ylwBins"].astype(str)
    df["categories"] = "age " + df["ageBins"].astype(str) + " ylw " + df["ylwBins"].astype(str)

    # attach bin colors (defined above)
    df = pd.merge(df, catColorDF, how="left", on="categories")
    df["categories"].astype("category", inplace=True)

    # attach counts per group
    dGroups = df.groupby("categories")
    groupDF = dGroups["hashID"].describe()
    groupDF["ageCategories"] = dGroups["ageCategories"].describe()["top"]
    groupDF["ylwCategories"] = dGroups["ylwCategories"].describe()["top"]
    #groupDF["ylwAlpha"] = dGroups["ylwAlpha"].mean()
    groupDF["allColors"] = dGroups["allColors"].describe()["top"]
    groupDF.reset_index(inplace=True)

    # attach group counts to the main dataframe
    df = pd.merge(df, groupDF[["categories", "count", "unique"]], how="left", on="categories")

    # remove all categories that do NOT have at least 10 unique people
    df = df[df["unique"] > min_unique_donors]
    groupDF = groupDF[groupDF["unique"] > min_unique_donors]

    # attach N and U to the categories
    df["categoriesFull"] = (
        df["categories"].astype(str) +
        " (N=" + df["count"].astype(str) +
        ", U=" + df["unique"].astype(str) +  ")"
    )

    return df, groupDF


# %% define age and years living with bins
group_title = "-withYlw0"
figure_path = os.path.join(".", "figures")

# next bin the data by age-ylw groups
dataGroupName = "age-ylw-groups"
ageBins = np.array([0,5,8,12,17,24,85])
ylwBins = np.array([-1,0,1,2,5,10,25,75])

# bin by age
ageGroupNames = []
for x, y in zip(ageBins[:-1]+1, ageBins[1:]):
    ageGroupNames.append("%s-%s"%(f"{x:02d}", f"{y:02d}"))

ylwGroupNames = []
for x, y in zip(ylwBins[:-1]+1, ylwBins[1:]):
    if x == y:
        ylwGroupNames.append("%s"%(f"{x:02d}"))
    else:
        ylwGroupNames.append("%s-%s"%(f"{x:02d}", f"{y:02d}"))

catColors = [
    '#f0d8e5','#f4bdd8','#f7a0cc','#f781bf',
    '#ebc3c1','#f1a095','#f17d6c','#ec5644','#e41a1c',
    '#f2d8c3','#fbc299','#ffac6f','#ff9746','#ff7f00',
    '#d0e1cc','#b8d8b2','#9fcd97','#86c37e','#6cb964','#4daf4a',
    '#c9d6e3','#afc4da','#95b1d2','#7aa0c9','#5b8fc1','#377eb8',
    '#dacbde','#d0b6d4','#c5a1ca','#ba8dc0','#af78b7','#a464ad','#984ea3'
]



finalCategories = [
        'age 01-05 ylw 00', 'age 01-05 ylw 01', 'age 01-05 ylw 02',
        'age 01-05 ylw 03-05', 'age 06-08 ylw 00', 'age 06-08 ylw 01',
        'age 06-08 ylw 02', 'age 06-08 ylw 03-05', 'age 06-08 ylw 06-10',
        'age 09-12 ylw 00', 'age 09-12 ylw 01', 'age 09-12 ylw 02',
        'age 09-12 ylw 03-05', 'age 09-12 ylw 06-10', 'age 13-17 ylw 00',
        'age 13-17 ylw 01', 'age 13-17 ylw 02', 'age 13-17 ylw 03-05',
        'age 13-17 ylw 06-10', 'age 13-17 ylw 11-25', 'age 18-24 ylw 00',
        'age 18-24 ylw 01', 'age 18-24 ylw 02', 'age 18-24 ylw 03-05',
        'age 18-24 ylw 06-10', 'age 18-24 ylw 11-25', 'age 25-85 ylw 00',
        'age 25-85 ylw 01', 'age 25-85 ylw 02', 'age 25-85 ylw 03-05',
        'age 25-85 ylw 06-10', 'age 25-85 ylw 11-25',
        'age 25-85 ylw 26-75'
]

catColorDF = pd.DataFrame(data=[finalCategories, catColors], index=["categories", "allColors"]).T


# %% load in summary donor data
dataPulledDate = "2019-01-10"
dataProcessedDate = "2019-01-22"

phiDate = "PHI-" + dataPulledDate
donorPath = os.path.join("..", "bigdata-processing-pipeline", "data", phiDate + "-donor-data")
donorList = phiDate + "-uniqueDonorList"
donors = pd.read_csv(os.path.join(donorPath, donorList + ".csv"), low_memory=False)


# %% all-donors summary
allAgeSummary = pd.DataFrame()
dataPath = os.path.join(donorPath, "settings-and-events")
d = pd.read_csv(os.path.join(dataPath, "combined-allMetadata.csv"), low_memory=False)

# attach the donor level data to the
allMetadata = pd.merge(
    d,
    donors[[
        "hashID",
        "userID",
        "diagnosisType",
        "targetDevices",
        "targetTimezone",
        "termsAccepted"
    ]],
    how="left",
    on="hashID"
)
allMetadata.to_csv(os.path.join(donorPath, donorList + "-w-metaData.csv"))


# %% load data
dayData = pd.read_csv(os.path.join(dataPath, "combined-dayData.csv"), low_memory=False)
bolusData = pd.read_csv(os.path.join(dataPath, "combined-bolusEvents.csv"), low_memory=False)
basalData = pd.read_csv(os.path.join(dataPath, "combined-basalEvents.csv"), low_memory=False)

# %% attach the diagnosis type to the day data
dayDF = pd.merge(
    dayData,
    allMetadata[[
        "hashID",
        "diagnosisType",
        "pump.top",
        "pumpSettings.isfLikelyUnits"
    ]],
    how="left",
    on="hashID"
)

dayDF = filter_data(dayDF, min_days_criteria=7)
dayDF, dayDFGroupSummary = (
    bin_data(
        dayDF,
        ageBins,
        ageGroupNames,
        ylwBins,
        ylwGroupNames,
        catColorDF,
        min_unique_donors=10
    )
)


# %% all-event level summary (max basal and max bolus)
# attach the day to bolus data and filter data by analysis criteria
# NOTE: seet the filter_data function for details
bolus = merge_dayData(bolusData, dayDF)
bolus = filter_data(bolus, min_days_criteria=7)
bolus, bolusGroupSummary = (
    bin_data(
        bolus,
        ageBins,
        ageGroupNames,
        ylwBins,
        ylwGroupNames,
        catColorDF,
        min_unique_donors=10
    )
)


# %% overview of bolus data table
figName = "overviewTable-bolus-events"
figName = figName + group_title
trace = go.Table(
    header=dict(
        values=make_bold(["AGE-YLW Group",
                          "Age",
                          "Years Living with T1D",
                          "N (Bolus Events)",
                          "U (Unique Donors)"]),
        align = ['center', 'center', 'center'],
        font = dict(color = 'black', size=14)
    ),
    cells=dict(
        values=[make_bold(bolusGroupSummary['categories']),
                make_bold(bolusGroupSummary['ageCategories']),
                make_bold(bolusGroupSummary['ylwCategories']),
                make_bold(bolusGroupSummary['count']),
                make_bold(bolusGroupSummary['unique'])],
        fill = dict(color = [bolusGroupSummary["allColors"]]),
        align = ['center', 'center', 'center'],
        font = dict(color = 'black', size=11),
        height = 22
    ),
)

fig = go.Figure()
fig.add_trace(trace)

pio.write_image(
    fig,
    os.path.join(
        figure_path,
        figName + "-highRes.png"
    ),
    width=1200,
    height=1200,
    scale=4)

pio.write_image(
    fig,
    os.path.join(
        figure_path,
        figName + "-lowRes.png"
    ),
    width=1200,
    height=1200,
    scale=1)


# %% max bolus amount ()
maxBolus = pd.DataFrame(bolus.groupby(["hashID", "day"])["unitsInsulin"].max()).reset_index()
maxBolus.rename(columns={"unitsInsulin":"maxBolusPerDay"}, inplace=True)

maxBolus = pd.merge(
    maxBolus,
    dayDF[[
        "hashID",
        "day",
        "categories",
        "allColors"
    ]],
    how="left",
    on=["hashID", "day"]
)

# remove nans in category as they represent data from days that did not meat the
# acceptable day standard
maxBolus = maxBolus[maxBolus["categories"].notnull()]

field = 'maxBolusPerDay'
yLabel = "Max Bolus Per Day (U)"
figName = "Max Bolus"
yMin = 0
yMax = 21
filteredDF = maxBolus[maxBolus[field] > 0].copy()

## make/save static summary table
figName = figName + group_title
nDecimalPlaces = 1
summaryTable, allAgeTable = make_static_table(
    field,
    figName,
    filteredDF,
    nDecimalPlaces,
    return_summaryTable=True
)

# add the ageTable to the allAgeSummary
allAgeSummary = pd.concat([allAgeSummary, allAgeTable], axis=0)

# add N events and n unique donors
filteredDF = pd.merge(
    filteredDF,
    summaryTable[[
        "categories",
        "count",
        "unique"
    ]],
    how="left",
    on="categories"
)

## make/save static boxplot
make_static_plot(field, yLabel, figName, filteredDF, yMin, yMax)

# make lite interactive plot
make_lite_interactive_boxplot(field, yLabel, filteredDF, yMin, yMax)


# %% basal data
basal = merge_dayData(basalData, dayDF)
basal = filter_data(basal, min_days_criteria=7)
basal, basalGroupSummary = (
    bin_data(
        basal,
        ageBins,
        ageGroupNames,
        ylwBins,
        ylwGroupNames,
        catColorDF,
        min_unique_donors=10
    )
)


# %% overview of basal data table
figName = "overviewTable-basal-events"
figName = figName + group_title

trace = go.Table(
    header=dict(
        values=make_bold(["AGE-YLW Group",
                          "Age",
                          "Years Living with T1D",
                          "N (Basal Events)",
                          "U (Unique Donors)"]),
        align = ['center', 'center', 'center'],
        font = dict(color = 'black', size=14)
    ),
    cells=dict(
        values=[make_bold(basalGroupSummary['categories']),
                make_bold(basalGroupSummary['ageCategories']),
                make_bold(basalGroupSummary['ylwCategories']),
                make_bold(basalGroupSummary['count']),
                make_bold(basalGroupSummary['unique'])],
        fill = dict(color = [basalGroupSummary["allColors"]]),
        align = ['center', 'center', 'center'],
        font = dict(color = 'black', size=11),
        height = 22
    ),
)

fig = go.Figure()
fig.add_trace(trace)

pio.write_image(
    fig,
    os.path.join(
        figure_path,
        figName + "-highRes.png"
    ),
    width=1200,
    height=1200,
    scale=4)

pio.write_image(
    fig,
    os.path.join(
        figure_path,
        figName + "-lowRes.png"
    ),
    width=1200,
    height=1200,
    scale=1)


# %% max basal rate
maxBasal = pd.DataFrame(basal[basal["type"]=="basal"].groupby(["hashID", "day"])["rate"].max()).reset_index()

maxBasal.rename(columns={"rate":"maxBasalRatePerDay"}, inplace=True)

maxBasal = pd.merge(
    maxBasal,
    dayDF[[
        "hashID",
        "day",
        "categories",
        "allColors"
    ]],
    how="left",
    on=["hashID", "day"]
)

# remove nans in category as they represent data from days that did not meat the
# acceptable day standard
maxBasal = maxBasal[maxBasal["categories"].notnull()]

field = 'maxBasalRatePerDay'
yLabel = "Max Basal Per Day (U/hr)"
figName = "Max Basal"
yMin = 0
yMax = 3.25
filteredDF = maxBasal[maxBasal[field] > 0].copy()

## make/save static summary table
figName = figName + group_title
nDecimalPlaces = 1
summaryTable, allAgeTable = make_static_table(
    field,
    figName,
    filteredDF,
    nDecimalPlaces,
    return_summaryTable=True
)

# add the ageTable to the allAgeSummary
allAgeSummary = pd.concat([allAgeSummary, allAgeTable], axis=0)

# add N events and n unique donors
filteredDF = pd.merge(
    filteredDF,
    summaryTable[[
        "categories",
        "count",
        "unique"
    ]],
    how="left",
    on="categories"
)

## make/save static boxplot
make_static_plot(field, yLabel, figName, filteredDF, yMin, yMax)

# make lite interactive plot
make_lite_interactive_boxplot(field, yLabel, filteredDF, yMin, yMax)


# %% overview of day level data table
figName = "overviewTable-day-data"
figName = figName + group_title

trace = go.Table(
    header=dict(
        values=make_bold(["AGE-YLW Group",
                          "Age",
                          "Years Living with T1D",
                          "N (Days)",
                          "U (Unique Donors)"]),
        align = ['center', 'center', 'center'],
        font = dict(color = 'black', size=14)
    ),
    cells=dict(
        values=[make_bold(dayDFGroupSummary['categories']),
                make_bold(dayDFGroupSummary['ageCategories']),
                make_bold(dayDFGroupSummary['ylwCategories']),
                make_bold(dayDFGroupSummary['count']),
                make_bold(dayDFGroupSummary['unique'])],
        fill = dict(color = [dayDFGroupSummary["allColors"]]),
        align = ['center', 'center', 'center'],
        font = dict(color = 'black', size=11),
        height = 22
    ),
)

fig = go.Figure()
fig.add_trace(trace)

pio.write_image(
    fig,
    os.path.join(
        figure_path,
        figName + "-highRes.png"
    ),
    width=1200,
    height=1200,
    scale=4)

pio.write_image(
    fig,
    os.path.join(
        figure_path,
        figName + "-lowRes.png"
    ),
    width=1200,
    height=1200,
    scale=1)


# %% Average ISF per day
dayDF["isfRounded"] = dayDF['isf.weightedMean'].round(1)
field = 'isfRounded'
yLabel = "Insulin Sensitivity Factor (mg/dL/U)"
figName = "Insulin Sensitivity Factor"
yMin = 0
yMax = 400
filteredDF = dayDF[dayDF[field] > 0].copy()

# make/save static summary table
figName = figName + group_title
nDecimalPlaces = 0
summaryTable, allAgeTable = make_static_table(
    field,
    figName,
    filteredDF,
    nDecimalPlaces,
    return_summaryTable=True
)

# add the ageTable to the allAgeSummary
allAgeSummary = pd.concat([allAgeSummary, allAgeTable], axis=0)

## make/save static boxplot
make_static_plot(field, yLabel, figName, filteredDF, yMin, yMax)

# make lite interactive plot
make_lite_interactive_boxplot(field, yLabel, filteredDF, yMin, yMax)


# %% Average CIR per day
field = 'cir.weightedMean'
yLabel = "Carb to Insulin Ratio (g/U)"
figName = "Carb to Insulin Ratio"
yMin = 0
yMax = 70
filteredDF = dayDF[dayDF[field] > 0].copy()

# make/save static summary table
figName = figName + group_title
nDecimalPlaces = 1
summaryTable, allAgeTable = make_static_table(
    field,
    figName,
    filteredDF,
    nDecimalPlaces,
    return_summaryTable=True
)

# add the ageTable to the allAgeSummary
allAgeSummary = pd.concat([allAgeSummary, allAgeTable], axis=0)

## make/save static boxplot
make_static_plot(field, yLabel, figName, filteredDF, yMin, yMax)

# make lite interactive plot
make_lite_interactive_boxplot(field, yLabel, filteredDF, yMin, yMax)


# %% Average Correction Target per day
field = 'ct.target.weightedMean'
yLabel = "Correction Target (mg/dL)"
figName = "Correction Target"
yMin = 70
yMax = 180
filteredDF = dayDF[dayDF[field] > 0].copy()

# make/save static summary table
figName = figName + group_title
nDecimalPlaces = 0
summaryTable, allAgeTable = make_static_table(
    field,
    figName,
    filteredDF,
    nDecimalPlaces,
    return_summaryTable=True
)

# add the ageTable to the allAgeSummary
allAgeSummary = pd.concat([allAgeSummary, allAgeTable], axis=0)

## make/save static boxplot
make_static_plot(field, yLabel, figName, filteredDF, yMin, yMax)

# make lite interactive plot
make_lite_interactive_boxplot(field, yLabel, filteredDF, yMin, yMax)


# %% Average Basal Rate per day
field = 'sbr.weightedMean'
yLabel = "Scheduled Basal Rate (U/hr)"
figName = "Scheduled Basal Rate"
yMin = 0
yMax = 2.5
filteredDF = dayDF[dayDF[field] > 0].copy()

# make/save static summary table
figName = figName + group_title
nDecimalPlaces = 3
summaryTable, allAgeTable = make_static_table(
    field,
    figName,
    filteredDF,
    nDecimalPlaces,
    return_summaryTable=True
)

# add the ageTable to the allAgeSummary
allAgeSummary = pd.concat([allAgeSummary, allAgeTable], axis=0)

## make/save static boxplot
make_static_plot(field, yLabel, figName, filteredDF, yMin, yMax)

# make lite interactive plot
make_lite_interactive_boxplot(field, yLabel, filteredDF, yMin, yMax)


# %% Total Daily Dose
field = "totalAmountOfInsulin"
yLabel = "Total Daily Dose (U)"
figName = "Total Daily Dose"
yMin = 0
yMax = 125
filteredDF = dayDF[dayDF[field] > 0].copy()

# make/save static summary table
figName = figName + group_title
nDecimalPlaces = 1
summaryTable, allAgeTable = make_static_table(
    field,
    figName,
    filteredDF,
    nDecimalPlaces,
    return_summaryTable=True
)

# add the ageTable to the allAgeSummary
#allAgeSummary = pd.concat([allAgeSummary, allAgeTable], axis=0)

## make/save static boxplot
make_static_plot(field, yLabel, figName, filteredDF, yMin, yMax)

# make lite interactive plot
make_lite_interactive_boxplot(field, yLabel, filteredDF, yMin, yMax)


# %% Percent Basal
dayDF["perecentBasalInPercent"] = dayDF["percentBasal"] * 100
field = "perecentBasalInPercent"
yLabel = "Basal Proportion of Total Daily Dose (%)"
figName = "Basal Proportion of Total Daily Dose"
yMin = 0
yMax = 100
filteredDF = dayDF[dayDF[field] >= 0].copy()

# make/save static summary table
figName = figName + group_title
nDecimalPlaces = 1
summaryTable, allAgeTable = make_static_table(
    field,
    figName,
    filteredDF,
    nDecimalPlaces,
    return_summaryTable=True
)

# add the ageTable to the allAgeSummary
#allAgeSummary = pd.concat([allAgeSummary, allAgeTable], axis=0)

## make/save static boxplot
make_static_plot(field, yLabel, figName, filteredDF, yMin, yMax)

# make lite interactive plot
make_lite_interactive_boxplot(field, yLabel, filteredDF, yMin, yMax)


# %% Total Daily Carbs
field = "totalDailyCarbs"
yLabel = "Total Daily Carbs (g)"
figName = "Total Daily Carbs"
yMin = 0
yMax = 600
filteredDF = dayDF[dayDF[field] >= 0].copy()

# make/save static summary table
figName = figName + group_title
nDecimalPlaces = 0
summaryTable, allAgeTable = make_static_table(
    field,
    figName,
    filteredDF,
    nDecimalPlaces,
    return_summaryTable=True
)

# add the ageTable to the allAgeSummary
#allAgeSummary = pd.concat([allAgeSummary, allAgeTable], axis=0)

## make/save static boxplot
make_static_plot(field, yLabel, figName, filteredDF, yMin, yMax)

# make lite interactive plot
make_lite_interactive_boxplot(field, yLabel, filteredDF, yMin, yMax)


# %% Daily Time in Range (70-180 mg/dL)
dayDF["perecentInRange"] = dayDF["cgm.percent70to180"] * 100
field = "perecentInRange"
yLabel = "Percent of Day in Targe Range (70-180 mg/dL, %)"
figName = "Percent of Day in Targe Range 70-180"
yMin = 0
yMax = 100
filteredDF = dayDF[dayDF[field] >= 0].copy()

# make/save static summary table
figName = figName + group_title
nDecimalPlaces = 1
summaryTable, allAgeTable = make_static_table(
    field,
    figName,
    filteredDF,
    nDecimalPlaces,
    return_summaryTable=True
)

# add the ageTable to the allAgeSummary
#allAgeSummary = pd.concat([allAgeSummary, allAgeTable], axis=0)

## make/save static boxplot
make_static_plot(field, yLabel, figName, filteredDF, yMin, yMax)

# make lite interactive plot
make_lite_interactive_boxplot(field, yLabel, filteredDF, yMin, yMax)


# %% Mean CGM (mg/dL)
field = "cgm.mean_mgdL"
yLabel = "Daily Average CGM Level (mg/dL)"
figName = "Daily Average CGM Level"
yMin = 50
yMax = 300
filteredDF = dayDF[dayDF[field] >= 0].copy()

# make/save static summary table
figName = figName + group_title
nDecimalPlaces = 0
summaryTable, allAgeTable = make_static_table(
    field,
    figName,
    filteredDF,
    nDecimalPlaces,
    return_summaryTable=True
)

# add the ageTable to the allAgeSummary
#allAgeSummary = pd.concat([allAgeSummary, allAgeTable], axis=0)

## make/save static boxplot
make_static_plot(field, yLabel, figName, filteredDF, yMin, yMax)

# make lite interactive plot
make_lite_interactive_boxplot(field, yLabel, filteredDF, yMin, yMax)


# %% Cov CGM (mg/dL)
dayDF["covPercent"] = dayDF["cgm.cov_mgdL"] * 100
field = "covPercent"
yLabel = "Coeffient of Variation (%)"
figName = "Coeffient of Variation"
yMin = 6
yMax = 62
filteredDF = dayDF[dayDF[field] >= 0].copy()

# make/save static summary table
figName = figName + group_title
nDecimalPlaces = 1
summaryTable, allAgeTable = make_static_table(
    field,
    figName,
    filteredDF,
    nDecimalPlaces,
    return_summaryTable=True
)

# add the ageTable to the allAgeSummary
#allAgeSummary = pd.concat([allAgeSummary, allAgeTable], axis=0)

## make/save static boxplot
make_static_plot(field, yLabel, figName, filteredDF, yMin, yMax)

# make lite interactive plot
make_lite_interactive_boxplot(field, yLabel, filteredDF, yMin, yMax)


# %% Daily Time Below 54 (Percentage)
dayDF["perecentBelow54mgdL"] = dayDF["cgm.percentBelow54"] * 100
field = "perecentBelow54mgdL"
yLabel = "Percent of Day Below 54 mg/dL (%)"
figName = "Percent of Day in Extreme Hypo Below 54 mgdL"
yMin = 0
yMax = 5
filteredDF = dayDF[dayDF[field] >= 0].copy()

# make/save static summary table
figName = figName + group_title
nDecimalPlaces = 2
summaryTable, allAgeTable = make_static_table(
    field,
    figName,
    filteredDF,
    nDecimalPlaces,
    return_summaryTable=True
)

# add the ageTable to the allAgeSummary
#allAgeSummary = pd.concat([allAgeSummary, allAgeTable], axis=0)

## make/save static boxplot
make_static_plot(field, yLabel, figName, filteredDF, yMin, yMax)

# make lite interactive plot
make_lite_interactive_boxplot(field, yLabel, filteredDF, yMin, yMax)


# %% Number of Below 54 mg/dL Episodes per Day
field = "extreme-hypo.count"
dayDF[field].fillna(0, inplace=True)
yLabel = "Number of Extreme Hypo Episodes (Below 54 mg/dL) per Day"
figName =  "Number of Extreme Hypo Episodes per Day"
yMin = 0
yMax = 2
filteredDF = dayDF[dayDF[field] >= 0].copy()

# make/save static summary table
figName = figName + group_title
nDecimalPlaces = 1
summaryTable, allAgeTable = make_static_table(
    field,
    figName,
    filteredDF,
    nDecimalPlaces,
    return_summaryTable=True
)

# add the ageTable to the allAgeSummary
#allAgeSummary = pd.concat([allAgeSummary, allAgeTable], axis=0)

## make/save static boxplot
make_static_plot(field, yLabel, figName, filteredDF, yMin, yMax)

# make lite interactive plot
make_lite_interactive_boxplot(field, yLabel, filteredDF, yMin, yMax)


# %% Average Duration of each Episode Below 54 mg/dL
field = "extreme-hypo-durationMinutes.mean"
yLabel = "Average Duration of each Extreme Hypo Episode (minutes)"
figName =  "Average Duration of each Extreme Hypo Episode"
yMin = 15
yMax = 120
filteredDF = dayDF[dayDF[field] >= 0].copy()

# make/save static summary table
figName = figName + group_title
nDecimalPlaces = 0
summaryTable, allAgeTable = make_static_table(
    field,
    figName,
    filteredDF,
    nDecimalPlaces,
    return_summaryTable=True
)

# add the ageTable to the allAgeSummary
#allAgeSummary = pd.concat([allAgeSummary, allAgeTable], axis=0)

## make/save static boxplot
make_static_plot(field, yLabel, figName, filteredDF, yMin, yMax)

# make lite interactive plot
make_lite_interactive_boxplot(field, yLabel, filteredDF, yMin, yMax)


# %% Daily Time Above 250 (Percentage)
dayDF["perecentAbove250mgdL"] = dayDF["cgm.percentAbove250"] * 100
field = "perecentAbove250mgdL"
yLabel = "Percent of Day Above 250 mg/dL (%)"
figName = "Percent of Day in Extreme Hyper Above 250 mgdL"
yMin = 0
yMax = 75
filteredDF = dayDF[dayDF[field] >= 0].copy()

# make/save static summary table
figName = figName + group_title
nDecimalPlaces = 0
summaryTable, allAgeTable = make_static_table(
    field,
    figName,
    filteredDF,
    nDecimalPlaces,
    return_summaryTable=True
)

# add the ageTable to the allAgeSummary
#allAgeSummary = pd.concat([allAgeSummary, allAgeTable], axis=0)

## make/save static boxplot
make_static_plot(field, yLabel, figName, filteredDF, yMin, yMax)

# make lite interactive plot
make_lite_interactive_boxplot(field, yLabel, filteredDF, yMin, yMax)


# %% Number of Above 250 mg/dL Episodes per Day
field = "extreme-hyper.count"
dayDF[field].fillna(0, inplace=True)
yLabel = "Number of Extreme Hyper Episodes (Above 250 mg/dL) per Day"
figName =  "Number of Extreme Hyper Episodes per Day"
yMin = 0
yMax = 2
filteredDF = dayDF[dayDF[field] >= 0].copy()

# make/save static summary table
figName = figName + group_title
nDecimalPlaces = 1
summaryTable, allAgeTable = make_static_table(
    field,
    figName,
    filteredDF,
    nDecimalPlaces,
    return_summaryTable=True
)

# add the ageTable to the allAgeSummary
#allAgeSummary = pd.concat([allAgeSummary, allAgeTable], axis=0)

## make/save static boxplot
make_static_plot(field, yLabel, figName, filteredDF, yMin, yMax)

# make lite interactive plot
make_lite_interactive_boxplot(field, yLabel, filteredDF, yMin, yMax)


# %% Average Duration of each Episode Above 250 mg/dL
dayDF["avgExtremeHyperHours"] = dayDF["extreme-hyper-durationMinutes.mean"] / 60
field = "avgExtremeHyperHours"
yLabel = "Average Duration of each Extreme Hyper Episode (hours)"
figName =  "Average Duration of each Extreme Hyper Episode"
yMin = 2
yMax = 10
filteredDF = dayDF[dayDF[field] >= 0].copy()

# make/save static summary table
figName = figName + group_title
nDecimalPlaces = 1
summaryTable, allAgeTable = make_static_table(
    field,
    figName,
    filteredDF,
    nDecimalPlaces,
    return_summaryTable=True
)

# add the ageTable to the allAgeSummary
#allAgeSummary = pd.concat([allAgeSummary, allAgeTable], axis=0)

## make/save static boxplot
make_static_plot(field, yLabel, figName, filteredDF, yMin, yMax)

# make lite interactive plot
make_lite_interactive_boxplot(field, yLabel, filteredDF, yMin, yMax)


# %% save the all age summaries
figName = "allAgeSettingSummary" + group_title
allAgeSummary.to_csv(
    os.path.join(
        figure_path,
        figName + "-all-age-table.csv"
    )
)

# %% make a plot of TDD by ISF

# Average ISF per day
dayDF["isfRounded"] = dayDF['isf.weightedMean'].round(1)
#field = 'isfRounded'
#yLabel = "Insulin Sensitivity Factor (mg/dL/U)"
#figName = "Insulin Sensitivity Factor"
#yMin = 0
#yMax = 400

## Total Daily Dose
#field = "totalAmountOfInsulin"
#yLabel = "Total Daily Dose (U)"
#figName = "Total Daily Dose"
#yMin = 0
#yMax = 125
#filteredDF = dayDF[dayDF[field] > 0].copy()

filteredDF = dayDF[((dayDF['isfRounded'] > 0) &
                    (dayDF['totalAmountOfInsulin'] > 0))].copy()

ylwColors = ["#ffffb2", '#fecc5c', '#fd8d3c', '#f03b20', '#bd0026']
for f in filteredDF["ylwCategories"].unique():
    if f == '00':
        colorCode = 0
    if f == '01':
        colorCode = 1
    if f == '02':
        colorCode = 2
    if f == '03-05':
        colorCode = 3
    else:
        colorCode = 4

    filteredDF.loc[filteredDF["ylwCategories"] == f, "ylwColor"] = ylwColors[colorCode]



from scipy.optimize import curve_fit
def func(x, a, b, c):
    return (a * x + b) / (x - 10)

import statsmodels.api as sm
lowess = sm.nonparametric.lowess
#a * np.exp(-b*x) + c * np.exp(-d * x)
#y = a * np.exp(-b * x) + c
#y = a * np.exp(b*x) + c * np.exp(d * x)

xdata = filteredDF['totalAmountOfInsulin'].round()
ydata = filteredDF['isfRounded']
popt, pcov = curve_fit(func, xdata, ydata)


x = np.arange(1, 500)
c = pd.DataFrame(columns=["ISF", "TDD"])
for xi in x:
    if sum(filteredDF['isfRounded'] == xi) > 3:
        c.loc[xi, "ISF"] = xi
        c.loc[xi, "TDD"] = filteredDF.loc[
            filteredDF['isfRounded'] == xi,
            "totalAmountOfInsulin"].median()

asdf2 = c.rolling(25, center=True).mean()
plt.plot(asdf2["TDD"], asdf2["ISF"])

x = np.arange(1, 300)
d = pd.DataFrame(columns=["TDD", "ISF"])
for xi in x:
    if sum(filteredDF['totalAmountOfInsulin'].round() == xi) > 3:
        d.loc[xi, "TDD"] = xi
        d.loc[xi, "ISF"] = filteredDF.loc[
            filteredDF['totalAmountOfInsulin'].round() == xi,
            "isfRounded"].median()

# then smooth out the medians
asdf = d.rolling(10, center=True).mean()
plt.plot(asdf["TDD"], asdf["ISF"])


# try a different approach were we just do a smoothed line


z = lowess(ydata, xdata)
#>>> w = lowess(y, x, frac=1./3)
plt.plot(z[:,0], z[:,1])

plt.plot(
    x,
    func(x, *popt),
    'r-',
#    label='fit: a=%5.3f, b=%5.3f, c=%5.3f' % tuple(popt)
)

#df.sort_values("categories", inplace=True)

traces = []
traces.append(go.Scatter(
        y=ydata,
        x=xdata,
        name="Scatter",
        mode='markers',
        marker=dict(
            color=filteredDF["allColors"],
            opacity=0.125,
        ),
))

#traces.append(go.Scatter(
#        y=z2[:,0],
#        x=z2[:,1],
#        mode='lines',
#))
#
#traces.append(go.Scatter(
#        y=z[:,1],
#        x=z[:,0],
#        mode='lines',
#        line=dict(
#            color="black",
#        ),
#))

traces.append(go.Scatter(
        y=asdf["ISF"],
        x=asdf["TDD"],
        mode='lines',
        name="Trend by TDD",
        line=dict(
            color="black",
            dash="dot",
        ),
))

traces.append(go.Scatter(
        y=asdf2["ISF"],
        x=asdf2["TDD"],
        mode='lines',
        name="Trend by ISF",
        line=dict(
            color="black",
            dash="dash",
        ),
))

layout = go.Layout(
    font=dict(
        size=18
    ),
    xaxis=dict(
        title="TDD",
        dtick=20,
        range=[0, 300],
        showgrid=True,
        gridcolor='#f1f3f4',
        gridwidth=2,
        zeroline=True,
        zerolinecolor='#f1f3f4',
        zerolinewidth=2,
    ),
    yaxis=dict(
        title="ISF",
        dtick=20,
        range=[0, 500],
        showgrid=True,
        gridcolor='#f1f3f4',
        gridwidth=2,
        zeroline=True,
        zerolinecolor='#f1f3f4',
        zerolinewidth=2,
    )
)

fig = go.Figure(data=traces, layout=layout)
plot(fig)

for yd in df.categories.unique():
    traces.append(go.Box(
        y=df.loc[df["categories"] == yd, field].values,
        x=df.loc[df["categories"] == yd, "categories"].values,
        name=yd,
        boxpoints="all",
        notched=True,
        hoverlabel=dict(font=dict(size=22)),
        marker=dict(
            color=df.loc[df["categories"] == yd, "allColors"].describe()["top"],
            opacity=0,
        ),
    ))

layout = go.Layout(
    font=dict(
        size=22
    ),
    xaxis=dict(
        tickangle=52.5
    ),
    yaxis=dict(
        title=yLabel,
        range=[yMin, yMax],
        showgrid=True,
        gridcolor='#f1f3f4',
        gridwidth=2,
        zeroline=True,
        zerolinecolor='#f1f3f4',
        zerolinewidth=2,
    ),
    margin=dict(
        l=100,
        r=200,
        b=250,
        t=50,
    ),

    boxmode='group',
    showlegend=False,
    legend=dict(font=dict(size=14))
)

fig = go.Figure(data=traces, layout=layout)

save_fig(fig, figName + "-boxplot-lowRes", 1800, 1200, 1)
save_fig(fig, figName + "-boxplot-highRes", 1800, 1200, 4)








#filteredDF.plot.scatter(y="isfRounded", x="totalAmountOfInsulin", alpha=0.025)

# %% make a plot of TDD by max temp basal rate
maxBasal = pd.DataFrame(basal[basal["type"]=="basal"].groupby(["hashID", "day"])["rate"].max()).reset_index()

maxBasal.rename(columns={"rate":"maxBasalRatePerDay"}, inplace=True)

maxBasal = pd.merge(
    maxBasal,
    dayDF[[
        "hashID",
        "day",
        "categories",
        "allColors",
        "totalAmountOfInsulin",
        'basal.closedLoopDays'
    ]],
    how="left",
    on=["hashID", "day"]
)

# remove nans in category as they represent data from days that did not meat the
# acceptable day standard
#maxBasal = maxBasal[maxBasal["categories"].notnull()]




filteredDF = maxBasal[((maxBasal['totalAmountOfInsulin'] > 0) &
                    (maxBasal['maxBasalRatePerDay'] > 0))].copy()


filteredDF.plot.scatter(y="maxBasalRatePerDay", x="totalAmountOfInsulin", alpha=0.125)

