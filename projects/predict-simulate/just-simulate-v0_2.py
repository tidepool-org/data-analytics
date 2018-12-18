#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: predict and simulate
version: 0.0.2
created: 2018-12-15
author: Ed Nykaza
dependencies:
    * requires tidepool-analytics conda environment (see readme for instructions)
    * requires San Francisco Fonts in a ./fonts folder
license: BSD-2-Clause
"""


# %% required libraries
import pdb
import os
import sys
import pandas as pd
import numpy as np
import datetime as dt
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt
from matplotlib.legend_handler import HandlerLine2D
from matplotlib import lines
import matplotlib.font_manager as fm
import matplotlib.style as ms
ms.use("default")


# %% user inputs



# %% just simulate based upon inputs
def create_deltaBG_functions(deltaBgEquation):

    def get_deltaBG_function(ISF=0, BR=0, TB=0,
                             ACV=0, CIR=1, ABOLV=0,
                             AIV=0, deltaBgEquation=deltaBgEquation):

        return eval(deltaBgEquation)

    return get_deltaBG_function


def expand_settings(userInputArray, settingName, timeStepSize=5):
    # this will be user input (a simple table of the ISF schedule)
    userInputDf = pd.DataFrame(userInputArray,
                             columns=[settingName + ".time", settingName])

    # make sure the values are floats and not integers
    userInputDf[settingName] = userInputDf[settingName].astype("float")

    # expand the data to cover the entire date span
    settingDf = pd.DataFrame()
    for d in [-1, 0, 1]:
        userInputDf["dateTime"] = \
            pd.to_datetime(userInputDf[settingName + ".time"]) + pd.Timedelta(d, unit="D")
        settingDf = pd.concat([settingDf, userInputDf], ignore_index=True)

    # make sure times are rounded to the nearest 5 minutes
    settingDf["dateTime"] = settingDf["dateTime"].dt.round(str(timeStepSize) + "min")

    return settingDf


def merge_and_fill_data(settingDf, df):
    # merge df with the main contiguous 5 minute df frame
    df = pd.merge(df, settingDf, how="left", on="dateTime")
    # fill in the values
    df.fillna(method='ffill', inplace=True)
    return df


# %% define the model
deltaBgEquation = "ISF * ((ACV/CIR) - AIV)"
deltaBG = create_deltaBG_functions(deltaBgEquation)


# %% load in activity curve data
insulinActivityCurves = pd.read_csv("all-iac-models.csv", low_memory=False)
carbActivityCurves = pd.read_csv("all-cac-models.csv", low_memory=False)

# choose the insulin model that you want to use
insulinModel = insulinActivityCurves["adult"].values

# %% create a more realistic example with variable, boluses and basals
# first create a continuguous time series
currentTime=dt.datetime.now()
timeStepSize=5  # minutes
effectLength=8  # hours
roundedCurrentTime = pd.to_datetime(currentTime).round(str(timeStepSize) + "min")
startTime = roundedCurrentTime + pd.Timedelta(-24, unit="h")
endTime = roundedCurrentTime + pd.Timedelta(24, unit="h")
rng = pd.date_range(startTime, endTime, freq=(str(timeStepSize) + "min"))
data = pd.DataFrame(rng, columns=["dateTime"])
data["minutesRelativeToNow"] = np.arange(-24*60, 24*60 + 5,5)

# % ISF
userInputArray = np.array([["12:00 AM", 40],
                           ["12:00 PM", 50],
                           ["6:00 PM", 40]])

isf = expand_settings(userInputArray, "isf")
data = merge_and_fill_data(isf, data)

# % CIR
userInputArray = np.array([["12:00 AM", 10],
                           ["6:00 AM", 12],
                           ["10:00 AM", 10]])

cir = expand_settings(userInputArray, "cir")
data = merge_and_fill_data(cir, data)


# % SCHEDULED BASAL RATES (SBR)
userInputArray = np.array([["12:00 AM", 0.875],
                           ["6:00 AM", 1],
                           ["10:00 AM", 1]])

sbr = expand_settings(userInputArray, "sbr")
data = merge_and_fill_data(sbr, data)


# % ACTUAL BASALS INCLUDING TEMP BASALS AND SUSPENDS
userInputArray = np.array([["12:00 PM", 1.25, 360],
                           ["10:00 PM", 0, 30]])

# this will be user input (a simple table of the schedule)
userInputDf = pd.DataFrame(userInputArray,
                           columns=["abr.time",
                                    "abr",
                                    "duration"])

# make sure the values are floats and not integers
userInputDf["abr"] = userInputDf["abr"].astype("float")

# round to the nearest 5 minutes
userInputDf["dateTime"] = pd.to_datetime(userInputDf["abr.time"]).dt.round(str(timeStepSize) + "min")

abr = pd.DataFrame()
for b in range(len(userInputDf)):
    startTime = userInputDf.loc[b, "dateTime"]
    endTime = startTime + pd.Timedelta(np.int(userInputDf.loc[b, "duration"]), unit="m")
    rng = pd.date_range(startTime, endTime, freq=(str(timeStepSize) + "min"))
    tempDf = pd.DataFrame(rng[:-1], columns=["dateTime"])
    tempDf["abr"] = userInputDf.loc[b, "abr"]
    abr = pd.concat([abr, tempDf], ignore_index=True)

# merge data with data df
data = pd.merge(data, abr, how="left", on="dateTime")

# define the effective basal rate (U/hr)
data["ebr"] = (data.abr - data.sbr)
data["ebr"].fillna(0, inplace=True)
# define the effective basal rate (U/5min)
data["ebi"] = data["ebr"] / 12


# % BOLUSES
userInputArray = np.array([["8:00 AM", 2, 20, "lowGI"],
                           ["12:00 PM", 4, 40, "medGI"],
                           ["6:00 PM", 5, 50, "highGI"],
                           ["8:00 PM", 10, 100, "highGI"]])

# this will be user input (a simple table of the schedule)
boi = pd.DataFrame(userInputArray,
                           columns=["boi.time",
                                    "boi",
                                    "carbInput",
                                    "carbModel"])

# make sure the values are floats and not integers
boi["boi"] = boi["boi"].astype("float")
boi["carbInput"] = boi["carbInput"].astype("float")

# round to the nearest 5 minutes
boi["dateTime"] = pd.to_datetime(boi["boi.time"]).dt.round(str(timeStepSize) + "min")

# merge data with data df
data = pd.merge(data, boi, how="left", on="dateTime")
data["boi"].fillna(0, inplace=True)


# % merge basal and bolus insulin amounts together
data["tia"] = data["ebi"] + data["boi"]

# % calculate the insulin activity
data["aiv"] = 0
tempDf = data.loc[data["tia"] != 0, ["tia", "dateTime"]]
for amount, ind in zip(tempDf.tia, tempDf.index):
    aiv = pd.DataFrame(np.array([amount * insulinModel]).reshape(-1,1),
                       index=np.arange(ind,(ind + len(insulinModel))), columns=["aiv"])
    data.loc[ind:(ind + len(insulinModel)), ["aiv"]] = data["aiv"].add(aiv["aiv"], fill_value=0)

# % calculate the carb activity
data["acv"] = 0
tempDf = data.loc[data["carbInput"] > 0, ["carbInput", "carbModel", "dateTime"]]
for amount, model, ind in zip(tempDf["carbInput"], tempDf["carbModel"], tempDf.index):
    acv = pd.DataFrame(np.array([amount * carbActivityCurves[model]]).reshape(-1,1),
                       index=np.arange(ind,(ind + len(insulinModel))), columns=["acv"])
    data.loc[ind:(ind + len(insulinModel)), ["acv"]] = data["acv"].add(acv["acv"], fill_value=0)

# % at the end, need to window the contiguous data to the effect length
startTime = roundedCurrentTime + pd.Timedelta(-effectLength, unit="h")
endTime = roundedCurrentTime + pd.Timedelta(effectLength, unit="h")
rng = pd.date_range(startTime, endTime, freq=(str(timeStepSize) + "min"))
df = pd.DataFrame(rng, columns=["dateTime"])
df = pd.merge(df, data, how="left", on="dateTime")

# % make the prediction with the new data
df["bg"] = 180

df["dBG"] = deltaBG(ISF=df.isf.values,
                    CIR=df.cir.values,
                    ACV=df.acv.values,
                    AIV=df.aiv.values)

df["simulatedBG"] = df["bg"] + df["dBG"].cumsum()
df.loc[df["simulatedBG"] <= 40, "simulatedBG"] = 40
df.loc[df["simulatedBG"] >= 400, "simulatedBG"] = 400


# %% figure stuff
bgRange = [-40, 400]

versionNumber = 0.2
figureName = "Simulate-V" + str(versionNumber)
outputPath = os.path.join(".", "figures")

# create output folder if it doesn't exist
if not os.path.isdir(outputPath):
    os.makedirs(outputPath)

figureSizeInches = (15, 7)
figureFont = fm.FontProperties(fname=os.path.join(".", "fonts",
                                                  "SF Compact", "SFCompactText-Bold.otf"))
font = {'weight': 'bold',
        'size': 15}

plt.rc('font', **font)
coord_color = "#c0c0c0"

xLabel = "Time Relative to Now (Minutes)"
yLabel = "Glucose (mg/dL)"
labelFontSize = 18
tickLabelFontSize = 15


def common_figure_elements(ax, xLabel, yLabel, figureFont, labelFontSize, tickLabelFontSize, coord_color, yLabel_xOffset=0.4):
    # x-axis items
    ax.set_xlabel(xLabel, fontsize=labelFontSize, color=coord_color)

    # define the spines and grid
    ax.spines['bottom'].set_color(coord_color)
    ax.spines['top'].set_color(coord_color)
    ax.spines['left'].set_color(coord_color)
    ax.spines['right'].set_color(coord_color)
    ax.spines['bottom'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.grid(ls='-', color=coord_color)

    # set size of ticklabels
    ax.tick_params(axis='both', labelsize=tickLabelFontSize, colors=coord_color)

    # define labels and limits
    ax.text(min(ax.get_xlim()) - yLabel_xOffset,
            max(ax.get_ylim()) + abs(max(ax.get_ylim()) - min(ax.get_ylim()))/25,
            yLabel, fontproperties=figureFont, size=labelFontSize)

    return ax


# %% make the figure
fig, ax = plt.subplots(figsize=figureSizeInches)
plt.ylim(bgRange)
ax.set_xlim([min(df["minutesRelativeToNow"]), max(df["minutesRelativeToNow"])])

# plot the scheduled basal rates
ax.plot(df["minutesRelativeToNow"],
        df["ebr"]*20, linestyle="-", color="#f09a37", lw=3, label="Basal Rate")

# fill in temp basals and suspends
ax.fill_between(df["minutesRelativeToNow"], df["ebr"]*20, color="#f6cc89")

# plot the boluses
boluses = df.loc[pd.notna(df["boi.time"]),["minutesRelativeToNow", "boi"]]
for bolusIndex in boluses.index:
    ax.plot(df.loc[bolusIndex, "minutesRelativeToNow"],
            df.loc[bolusIndex, "simulatedBG"] + 15,
            marker='v', markersize=df.loc[bolusIndex, "boi"]*1.5, color="#f09a37",
            ls="None", label="%d Units of Insulin Delivered" % df.loc[bolusIndex, "boi"])

    # plot the carbs
    ax.plot(df.loc[bolusIndex, "minutesRelativeToNow"],
            df.loc[bolusIndex, "simulatedBG"] - 15,
            marker='^', markersize=df.loc[bolusIndex, "boi"]*1.5,
            color="#83d754", ls="None", label="%d Carbs" % df.loc[bolusIndex, "carbInput"])

# plot the active insulin
ax.plot(df["minutesRelativeToNow"],
        df["aiv"]*50+10, linestyle="-", color="#f09a37", lw=3, alpha=0.25, label="Active Insulin")

ax.fill_between(df["minutesRelativeToNow"], df["aiv"]*50+10, 10, color="#f6cc89", alpha=0.25)

# plot the active carbs
ax.plot(df["minutesRelativeToNow"],
        df["acv"]*10+30, linestyle="-", color="#83d754", lw=3, alpha=0.25, label="Active Carbs")

ax.fill_between(df["minutesRelativeToNow"], df["acv"]*10+30, 30, color="#bdeaa3", alpha=0.25)

# plot simulated cgm
ax.scatter(df["minutesRelativeToNow"], df["simulatedBG"], s=10, color="#31B0FF", label="Predicted BG Level")

# plot the current time
valueCurrentTime = df.loc[df["minutesRelativeToNow"] == 0, "simulatedBG"].values[0]
ax.plot(0, valueCurrentTime,
        marker='*', markersize=20, color=coord_color, markeredgecolor = "black", alpha=0.5,
        ls="None", label="Current Time BG =  %d" % (round(valueCurrentTime)))

# run the common figure elements here
ax = common_figure_elements(ax, xLabel, yLabel, figureFont, labelFontSize, tickLabelFontSize, coord_color, yLabel_xOffset=32)

# format the legend
leg = ax.legend(scatterpoints=3, edgecolor="black", loc="upper right")
for text in leg.get_texts():
    text.set_color('#606060')
    text.set_weight('normal')

plt.savefig(os.path.join(outputPath, figureName + ".png"))
plt.show()
plt.close('all')


