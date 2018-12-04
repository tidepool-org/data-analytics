#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: demonstrate the logic of the loop
version: 0.0.1
created: 2018-11-28
author: Ed Nykaza (original credit goes to Pete Schwamb, https://github.com/ps2/LoopExplain/blob/master/Loop%20Explain.ipynb)
dependencies:
    * requires tidepool-analytics environment (see readme for instructions)
    * requires San Francisco Fonts in a ./fonts folder
license: BSD-2-Clause
"""


# %% required libraries
import os
import sys
import pdb
import numpy as np
import pandas as pd
import datetime as dt
from scipy.interpolate import BSpline, make_interp_spline
from matplotlib import pyplot as plt
from matplotlib.legend_handler import HandlerLine2D
import matplotlib.font_manager as fm
import matplotlib.style as ms
ms.use("default")


# %% functions
def simulate_cgm_data(cgmTimesMinutes=[5, 120, 240, 360],
                      cgmValues_mgdL=[100, 95, 110, 105],
                      amountOfWiggle=3):

    inputCgm = pd.DataFrame(np.array([cgmTimesMinutes, cgmValues_mgdL]).T, columns=["time", "values"]).sort_values(by="time")
    simulatedTime = np.arange(inputCgm.time.min(), inputCgm.time.max() + 5, 5)
    splineProperties = make_interp_spline(inputCgm["time"].values,
                                          inputCgm["values"].values,
                                          k=amountOfWiggle)
    splineFit = BSpline(splineProperties.t, splineProperties.c, splineProperties.k)
    simulatedCgm = np.round(splineFit(simulatedTime))
    simulatedCgm[simulatedCgm <= 40] = 40
    simulatedCgm[simulatedCgm >= 400] = 400

    return simulatedTime, simulatedCgm


def make_hour_labels(startTimeHour, startTimeAMPM, hourTicks):
    labels = []
    if "AM" in startTimeAMPM:
        ampm = ["AM", "PM"]
    else:
        ampm = ["PM", "AM"]
    for label in hourTicks:
        hr = label + startTimeHour
        if hr == 0:
            hr = 12
            labels.append(("%d " + ampm[1]) % hr)
        elif hr == 12:
            labels.append(("%d " + ampm[1]) % hr)
        elif hr > 12:
            hr = hr - 12
            labels.append(("%d " + ampm[1]) % hr)

        else:  # case of ((hr >= 1) & (hr < 12)):
            labels.append(("%d " + ampm[0]) % hr)

    return labels


# %% insulin model functions
def exponentialModel(df, peakActivityTime, activeDuration=6):
    activeDurationMinutes = activeDuration * 60

    tau = (peakActivityTime *
           (1 - peakActivityTime / activeDurationMinutes) /
           (1 - 2 * peakActivityTime / activeDurationMinutes))
    a = 2 * tau / activeDurationMinutes
    S = 1 / (1 - a + (1 + a) * np.exp(-activeDurationMinutes / tau))

    df["iobPercent"] = (1 - S * (1 - a) *
      ((pow(df["minutesSinceDelivery"], 2) /
       (tau * activeDurationMinutes * (1 - a)) - df["minutesSinceDelivery"] / tau - 1) *
        np.exp(-df["minutesSinceDelivery"] / tau) + 1))

    return df


def get_insulin_effect(
        model="humalogNovologAdult",  # options are "walsh", "humalogNovologAdult",
        # "humalogNovologChild", "fiasp", or "exponentialCustom"
        activeDuration=6,  # in hours, only needs to be specified for walsh model,
        # can range between 2 to 8 hours in 15 minute increments
        peakActivityTime=np.nan,  # in minutes, only used for exponential model
        deliveryTime=dt.datetime.now(),  # date time of the insulin delivery
        insulinAmount=np.nan,  # units (U) of insulin delivered
        isf=np.nan,  # insulin sensitivity factor (mg/dL)/U
        effectLength=8,  # in hours, set to 8 because that is the max walsh model
        timeStepSize=5,  # in minutes, the resolution of the time series
        ):

    # specify the date range of the insulin effect time series
    startTime = pd.to_datetime(deliveryTime).round(str(timeStepSize) + "min")
    endTime = startTime + pd.Timedelta(8, unit="h")
    rng = pd.date_range(startTime, endTime, freq=(str(timeStepSize) + "min"))
    insulinEffect = pd.DataFrame(rng, columns=["dateTime"])

    insulinEffect["minutesSinceDelivery"] = np.arange(0, (effectLength * 60) + 1, timeStepSize)

    if "walsh" in model:
        if (activeDuration < 2) | (activeDuration > 8):
            sys.exit("invalid activeDuration, must be between 2 and 8 hours")
        elif activeDuration < 3:
            nearestActiveDuration = 3
        elif activeDuration > 6:
            nearestActiveDuration = 6
        else:
            nearestActiveDuration = round(activeDuration)

        # scale the time if the active duraiton is NOT 3, 4, 5, or 6 hours
        scaledMinutes = insulinEffect["minutesSinceDelivery"] * nearestActiveDuration / activeDuration

        if nearestActiveDuration == 3:

            # 3 hour model approximation
            insulinEffect["iobPercent"] = -3.2030e-9 * pow(scaledMinutes, 4) + \
                                            1.354e-6 * pow(scaledMinutes, 3) - \
                                            1.759e-4 * pow(scaledMinutes, 2) + \
                                            9.255e-4 * scaledMinutes + 0.99951

        elif nearestActiveDuration == 4:

            # 4 hour model approximation
            insulinEffect["iobPercent"] = -3.310e-10 * pow(scaledMinutes, 4) + \
                                            2.530e-7 * pow(scaledMinutes, 3) - \
                                            5.510e-5 * pow(scaledMinutes, 2) - \
                                            9.086e-4 * scaledMinutes + 0.99950

        elif nearestActiveDuration == 5:

            # 5 hour model approximation
            insulinEffect["iobPercent"] = -2.950e-10 * pow(scaledMinutes, 4) + \
                                            2.320e-7 * pow(scaledMinutes, 3) - \
                                            5.550e-5 * pow(scaledMinutes, 2) + \
                                            4.490e-4 * scaledMinutes + 0.99300
        elif nearestActiveDuration == 6:
            # 6 hour model approximation
            insulinEffect["iobPercent"] = -1.493e-10 * pow(scaledMinutes, 4) + \
                                            1.413e-7 * pow(scaledMinutes, 3) - \
                                            4.095e-5 * pow(scaledMinutes, 2) + \
                                            6.365e-4 * scaledMinutes + 0.99700
        else:
            sys.exit("this case should not happen")

    elif "humalogNovologAdult" in model:

        # peakActivityTime = 75 # 65, 55
        insulinEffect = exponentialModel(insulinEffect, 75)

    elif "humalogNovologChild" in model:

        # peakActivityTime = 75 # 65, 55
        insulinEffect = exponentialModel(insulinEffect, 65)

    elif "fiasp" in model:

        # peakActivityTime = 75 # 65, 55
        insulinEffect = exponentialModel(insulinEffect, 55)

    elif "exponentialCustom" in model:

        if peakActivityTime >= (activeDuration * 60):
            sys.exit("peak activity is greater than active duration, please note that " +
                     "peak activity is in minutes and active duration is in hours.")

        insulinEffect = exponentialModel(insulinEffect, peakActivityTime, activeDuration)

    # correct time at t=0
    insulinEffect.loc[insulinEffect["minutesSinceDelivery"] <= 0, "iobPercent"] = 1

    # correct times that are beyond the active duration
    insulinEffect.loc[insulinEffect["minutesSinceDelivery"] >= (activeDuration * 60), "iobPercent"] = 0

    # calculate the insulin on board
    insulinEffect["iob"] = insulinAmount * insulinEffect["iobPercent"]

    # calculate the change in blood glucose
    insulinEffect["cumulativeGlucoseEffect"] = -1 * (insulinAmount - insulinEffect["iob"]) * isf
    insulinEffect["deltaGlucoseEffect"] = \
        insulinEffect["cumulativeGlucoseEffect"] - insulinEffect["cumulativeGlucoseEffect"].shift()
    insulinEffect["deltaGlucoseEffect"].fillna(0, inplace=True)

    return insulinEffect


# %% set figure properties
versionNumber = 1

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

xLabel = "Time Since First Delivery (Hours)"
labelFontSize = 18
tickLabelFontSize = 15


# %% common figure elements across all figures
def common_figure_elements(ax, xLabel, yLabel, figureFont, labelFontSize, tickLabelFontSize, coord_color, yLabel_xOffset=0.4):
    # x-axis items
    ax.set_xlabel(xLabel, fontsize=labelFontSize, color=coord_color)
    ax.set_xlim(0, 8)

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


# %% define the insulin model and number of insulin boluses

# two insulin boluses example
figureClass = "LoopOverview-EffectTwoInsulinBolusesV" + str(versionNumber) + "-"

insulinModel = "humalogNovologAdult"
peakActivityTime = 60
activeDuration = 6
isf = 50

currentTime = dt.datetime.now()

# update this array to include when you want the insulin boluses to occer
deliveryTimeHoursRelativeToFirstDelivery = [0, 3]  # in hours
insulinAmount = [2, 3]

deliveryTime = list(map(lambda i: currentTime + pd.Timedelta(i, unit="h"), deliveryTimeHoursRelativeToFirstDelivery))
for bolusNumber in range(len(insulinAmount)):
    insulinEffect = get_insulin_effect(model=insulinModel,
                                       peakActivityTime=peakActivityTime,
                                       activeDuration=activeDuration,
                                       deliveryTime=deliveryTime[bolusNumber],
                                       insulinAmount=insulinAmount[bolusNumber],
                                       isf=isf)
    # append rows of insulinEffect into the cumulativeEffect
    if bolusNumber > 0:
        tempEffect = pd.concat([tempEffect, insulinEffect])
    else:
        tempEffect = insulinEffect.copy()

# take all of the insulin boluses and combine (add the effects)
dateTimeGroups = tempEffect.groupby("dateTime")
cumulativeInsulinEffect = dateTimeGroups.sum().reset_index(drop=False)
# drop the insulin on board percentage as it no longer has meaning
cumulativeInsulinEffect.drop(columns=["iobPercent", "minutesSinceDelivery"], inplace=True)

# add a column minutesSinceFirstDelivery
cumulativeInsulinEffect["minutesSinceFirstDelivery"] = \
    np.arange(0, len(cumulativeInsulinEffect)* 5, 5)

# recalculate the cumulative effect of BG
cumulativeInsulinEffect["cumulativeGlucoseEffect"] = \
    cumulativeInsulinEffect["deltaGlucoseEffect"].cumsum()

xData = cumulativeInsulinEffect["minutesSinceFirstDelivery"]/60


# %% iob
figureName = "iob-amount"
yLabel = "Insulin-On-Board (U)"
fig, ax = plt.subplots(figsize=figureSizeInches)

# fill the area under the curve with light orange
ax.fill_between(xData, 0, cumulativeInsulinEffect["iob"], color="#f6cc89")

# plot the curve
ax.plot(xData, cumulativeInsulinEffect["iob"], lw=4, color="#f09a37")

# run the common figure elements here
ax = common_figure_elements(ax, xLabel, yLabel, figureFont, labelFontSize, tickLabelFontSize, coord_color)

# show the insulin delivered
for bolusNumber in range(len(insulinAmount)):
    ax.plot(deliveryTimeHoursRelativeToFirstDelivery[bolusNumber],
            cumulativeInsulinEffect.loc[int(deliveryTimeHoursRelativeToFirstDelivery[bolusNumber] * 60 / 5), "iob"] + 0.15,
            marker='v', markersize=16, color="#f09a37",
            ls="None", label="%d Units of Insulin Delivered" % insulinAmount[bolusNumber])

    ax.text(deliveryTimeHoursRelativeToFirstDelivery[bolusNumber],
            cumulativeInsulinEffect.loc[int(deliveryTimeHoursRelativeToFirstDelivery[bolusNumber] * 60 / 5), "iob"] + 0.3,
            "%d Units Delivered" % insulinAmount[bolusNumber],
            horizontalalignment="left", fontproperties=figureFont, size=labelFontSize, color=coord_color)


plt.xlim([min(xData) - 0.1, max(xData)])
# save the figure
plt.savefig(os.path.join(outputPath, figureClass + figureName + ".png"))
plt.show()
plt.close('all')


# %% delta BG
figureName = "delta-bg"
yLabel = "Change in BG (mg/dL) every 5 minutes"
fig, ax = plt.subplots(figsize=figureSizeInches)

# plot the curve
ax.scatter(xData, cumulativeInsulinEffect["deltaGlucoseEffect"], color="#f09a37")

# run the common figure elements here
ax = common_figure_elements(ax, xLabel, yLabel, figureFont, labelFontSize, tickLabelFontSize, coord_color)


# show the insulin delivered
for bolusNumber in range(len(insulinAmount)):
    ax.plot(deliveryTimeHoursRelativeToFirstDelivery[bolusNumber],
            cumulativeInsulinEffect.loc[int(deliveryTimeHoursRelativeToFirstDelivery[bolusNumber] * 60 / 5), "deltaGlucoseEffect"] + 0.2,
            marker='v', markersize=16, color="#f09a37",
            ls="None", label="%d Units of Insulin Delivered" % insulinAmount[bolusNumber])

    ax.text(deliveryTimeHoursRelativeToFirstDelivery[bolusNumber] + 0.1,
            cumulativeInsulinEffect.loc[int(deliveryTimeHoursRelativeToFirstDelivery[bolusNumber] * 60 / 5), "deltaGlucoseEffect"] + 0.1,
            "%d Units Delivered" % insulinAmount[bolusNumber],
            horizontalalignment="left", fontproperties=figureFont, size=labelFontSize, color=coord_color)


# extras for this plot
ax.set_xlim(-0.1, 10)

# save the figure
plt.savefig(os.path.join(outputPath, figureClass + figureName + ".png"))
plt.show()
plt.close('all')


# %% cumulative glucose effect
figureName = "cumulative-insulin-effect"
yLabel = "Cumulative Insulin Effect on BG (mg/dL)"
fig, ax = plt.subplots(figsize=figureSizeInches)

# plot the curve
ax.plot(xData, cumulativeInsulinEffect["cumulativeGlucoseEffect"], lw=4, color="#f09a37")

# run the common figure elements here
ax = common_figure_elements(ax, xLabel, yLabel, figureFont, labelFontSize, tickLabelFontSize, coord_color)

# extras for this plot
ax.set_xlim(-0.1, 10)

# show the insulin delivered
for bolusNumber in range(len(insulinAmount)):
    ax.plot(deliveryTimeHoursRelativeToFirstDelivery[bolusNumber],
            cumulativeInsulinEffect.loc[int(deliveryTimeHoursRelativeToFirstDelivery[bolusNumber] * 60 / 5), "cumulativeGlucoseEffect"],
            marker='v', markersize=16, color="#f09a37",
            ls="None", label="%d Units of Insulin Delivered" % insulinAmount[bolusNumber])

    ax.text(deliveryTimeHoursRelativeToFirstDelivery[bolusNumber] + 0.1,
            cumulativeInsulinEffect.loc[int(deliveryTimeHoursRelativeToFirstDelivery[bolusNumber] * 60 / 5), "cumulativeGlucoseEffect"] + 5,
            "%d Units Delivered" % insulinAmount[bolusNumber],
            horizontalalignment="left", fontproperties=figureFont, size=labelFontSize, color=coord_color)


# save the figure
plt.savefig(os.path.join(outputPath, figureClass + figureName + ".png"))
plt.show()
plt.close('all')


# %% now show example with the previous plot

# specify the CGM Data (in minutes and mg/dL)
cgmTimes =  [5,    30, 60, 75, 100, 120, 150, 180]
cgmValues = [250, 290, 330, 350, 360, 345, 355, 355]
simulatedTime, simulatedCgm = simulate_cgm_data(cgmTimes, cgmValues, amountOfWiggle=2)

# specify the time you want the simulation to start
startTimeHour = 6
startTimeAMPM = "AM"

## %% apply the insulin effect
predictedTime = np.arange(185, 185 + len(cumulativeInsulinEffect) * 5, 5)
predictedCgm = 355 + np.round(cumulativeInsulinEffect["cumulativeGlucoseEffect"].values)

# make the figure
figureName = "insulin-effect-example"
fig, ax = plt.subplots(figsize=figureSizeInches)
plt.ylim((80, 400))
yLabel = "Glucose (mg/dL)"

# plot correction range
correction_min = 90
correction_max = 120

# plot correction range
ax.fill_between(np.arange(0, (len(simulatedCgm) + len(predictedCgm)) * 5, 5),
                correction_min,
                correction_max,
                facecolor='#bde5fc', lw=0)

ax.plot([], [], color='#bde5fc', linewidth=10,
        label="Correction Range: %d-%d" % (correction_min, correction_max))

## show the insulin delivered
#ax.plot(predictedTime[0] - 5, predictedCgm[0] + 5,
#        marker='v', markersize=16, color="#f09a37",
#        ls="None", label="%d Units of Insulin Delivered" % insulinAmount)

# show the insulin delivered
for bolusNumber in range(len(insulinAmount)):
    ax.plot(180 + deliveryTimeHoursRelativeToFirstDelivery[bolusNumber] * 60,
            cumulativeInsulinEffect.loc[int(deliveryTimeHoursRelativeToFirstDelivery[bolusNumber] * 60 / 5), "cumulativeGlucoseEffect"] + 365,
            marker='v', markersize=16, color="#f09a37",
            ls="None", label="%d Units of Insulin Delivered" % insulinAmount[bolusNumber])

# plot predicted cgm
ax.plot(predictedTime, predictedCgm, linestyle="--", color="#4faef8", lw=4, label="Prediction (Insulin Effect Only)")

# plot eventual bg
ax.plot(predictedTime[-1], predictedCgm[-1],
        marker='*', markersize=16, color="#4faef8",
        ls="None", label="Eventual BG = %d" % predictedCgm[-1])

# plot simulated cgm
ax.scatter(simulatedTime, simulatedCgm, s=18, color="#4faef8", label="CGM Data")

# define the legend
leg = plt.legend(scatterpoints=3, edgecolor="black")
for text in leg.get_texts():
    text.set_color('#606060')
    text.set_weight('normal')

# run the common figure elements here
ax = common_figure_elements(ax, xLabel, yLabel, figureFont, labelFontSize, tickLabelFontSize, coord_color, yLabel_xOffset=50)

# extras for this plot
ax.set_xlabel("")
plt.xlim([min(simulatedTime) - 15, max(predictedTime) + 15])
ax.text(max(ax.get_xlim()),
        max(ax.get_ylim()) + 7,
        "Eventually %d mg/dL" % predictedCgm[-1],
        horizontalalignment="right", fontproperties=figureFont, size=labelFontSize, color=coord_color)

# set tick marks
minuteTicks = np.arange(0, (len(simulatedTime) + len(predictedTime)) * 5 + 1, 60)
hourTicks = np.int64(minuteTicks / 60)
hourLabels = make_hour_labels(startTimeHour, startTimeAMPM, hourTicks)
ax.set_xticks(minuteTicks)
ax.set_xticklabels(hourLabels)

plt.savefig(os.path.join(outputPath, figureClass + figureName + ".png"))
plt.show()
plt.close('all')

# %%



