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
import matplotlib.patches as mpatches
from matplotlib.collections import PatchCollection
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
        timeStepSize=5*60,  # in seconds, the resolution of the time series, default is every 5 min
        ):

    # TODO: ISF needs to be a function of time

    # specify the date range of the insulin effect time series
    startTime = pd.to_datetime(deliveryTime).round(str(timeStepSize) + "s")
    endTime = startTime + pd.Timedelta(8, unit="h")
    rng = pd.date_range(startTime, endTime, freq=(str(timeStepSize) + "s"))
    insulinEffect = pd.DataFrame(rng[:-1], columns=["dateTime"])

    insulinEffect["secondsSinceDelivery"] = np.arange(0, (effectLength * 60 * 60), timeStepSize)
    insulinEffect["minutesSinceDelivery"] = insulinEffect["secondsSinceDelivery"] / 60
    insulinEffect["hoursSinceDelivery"] = insulinEffect["minutesSinceDelivery"] / 60

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
    insulinEffect["normalizedCumulativeGlucoseEffect"] = -1 * (insulinAmount - insulinEffect["iob"])

    insulinEffect["normalizedDeltaGlucoseEffect"] = \
        insulinEffect["normalizedCumulativeGlucoseEffect"] - \
        insulinEffect["normalizedCumulativeGlucoseEffect"].shift()

    insulinEffect["normalizedDeltaGlucoseEffect"].fillna(0, inplace=True)

    # if an isf is given then calculate the actual effect
    if ~np.isnan(isf):
        insulinEffect["cumulativeGlucoseEffect"] = insulinEffect["normalizedCumulativeGlucoseEffect"] * isf
        insulinEffect["deltaGlucoseEffect"] = insulinEffect["normalizedDeltaGlucoseEffect"] * isf

    return insulinEffect


def get_basal_insulin_effect(basalStartTime, basalRate, durationMilliSeconds, pumpModel, insulinModel):
    # get the minimum increment for the pump
    # TODO: confirm this is how these pumps implement basal rates
    if pumpModel in ["523", "723", "554", "754"]:
        minIncrement = 0.025
    else:  #  includes MM 515, 715, 522, 722
        minIncrement = 0.05

    # handle the negative basal rate case
    if basalRate < 0:
        basalRate = abs(basalRate)
        isNegativeBasalRate = "True"
    else:
        isNegativeBasalRate = "False"

    if basalRate < 1:
        deliveryIncrement = minIncrement
    elif basalRate < 10:
        deliveryIncrement = 0.05
    else:  # 1% of the rate, but I assume it must be rounded to the nearest minimum increment
        deliveryIncrement = np.round(np.round((basalRate * 0.01) / minIncrement) * minIncrement, 3)

    # delivery of insulin
    if basalRate > 0:
        durationHours = durationMilliSeconds / (60 * 60 * 1000)
        totalInsulinToDeliver = basalRate * durationHours
        nDeliveries = int(np.floor(totalInsulinToDeliver / deliveryIncrement))
        if nDeliveries == 0:
            nDeliveries = 1
        durationSeconds = round(durationMilliSeconds / 1000)
        deliveryFreq = int(durationSeconds / nDeliveries)
        deliveryTimes = pd.date_range(basalStartTime, periods=nDeliveries, freq=str(deliveryFreq) + "s")
        basalInsulin = pd.DataFrame(deliveryTimes, columns=["dateTime"])
        basalInsulin["deliveryAmount"] = deliveryIncrement

        # first delivery
        insulinEffect = get_insulin_effect(model=insulinModel,
                                           deliveryTime=deliveryTimes[0],
                                           insulinAmount=deliveryIncrement,
                                           timeStepSize=1)

        # combine the effects
        combinedInsulinEffect = insulinEffect[["dateTime", "iob","normalizedDeltaGlucoseEffect"]].copy()
        tempInsulinEffect = combinedInsulinEffect.copy()
        for iDelivery in range(1, nDeliveries):
            tempInsulinEffect["dateTime"] = insulinEffect.dateTime + pd.Timedelta(deliveryFreq * iDelivery, unit="s")
            combinedInsulinEffect = pd.concat([combinedInsulinEffect, tempInsulinEffect])

        # combine the effects
        dateTimeGroups = combinedInsulinEffect.groupby("dateTime")
        basalInsulinEffectSeconds = dateTimeGroups.sum()

        # resample the results to give the expected drop every 5 minutes
        basalInsulinEffect = \
            basalInsulinEffectSeconds["normalizedDeltaGlucoseEffect"].resample("5min", closed="right", label="right").sum().reset_index()
        basalIob = \
            basalInsulinEffectSeconds["iob"].resample("5min", closed="right", label="right").max().reset_index()

        if isNegativeBasalRate == "True":
            basalInsulinEffect["normalizedDeltaGlucoseEffect"] = basalInsulinEffect["normalizedDeltaGlucoseEffect"] * -1
            basalInsulinEffect["iob"] = 0
        else:
            basalInsulinEffect["iob"] = basalIob["iob"].copy()

    else:  # basalRate is 0
        deliveryTimes = pd.date_range(basalStartTime, periods=6*20, freq="5min")
        basalInsulinEffect = pd.DataFrame(deliveryTimes, columns=["dateTime"])
        basalInsulinEffect["normalizedDeltaGlucoseEffect"] = 0
        basalInsulinEffect["iob"] = 0

    basalInsulinEffect["normalizedCumulativeGlucoseEffect"] = \
        basalInsulinEffect["normalizedDeltaGlucoseEffect"].cumsum()

    basalInsulinEffect["minutesSinceBasalStart"] = np.arange(0, len(basalInsulinEffect) * 5, 5)
    basalInsulinEffect["hoursSinceBasalDelivery"] = basalInsulinEffect["minutesSinceBasalStart"] / 60

    return basalInsulinEffect


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
            max(ax.get_ylim()) + abs(max(ax.get_ylim()) - min(ax.get_ylim()))/12.5,
            yLabel, fontproperties=figureFont, size=labelFontSize)

    return ax


# %% combine multiple basal rates and boluses over time
figureName = "basal-insulin-effect"
yLabel = "Basal Rates & IOB"
fig, ax = plt.subplots(figsize=figureSizeInches)

pumpModel = "723"
insulinModel = "humalogNovologAdult"

basalData = pd.read_csv("basalExample.csv", low_memory=False)

# NOTE: this example assumes that suspends have a rate of 0.
# Tidepool data will mark the rate as nan; use the commented code to replace nan with 0
## fill NaNs with 0, as it indicates a temp basal of 0
#basalData.rate.fillna(0, inplace=True)

basalData["deliveryTimeHoursRelativeToFirstDelivery"] = \
    (pd.to_datetime(basalData["est.localTime"]) - \
     pd.to_datetime(basalData.loc[0, "est.localTime"])).dt.total_seconds() / (3600)

combinedInsulinEffect = pd.DataFrame(columns=["dateTime", "iob", "normalizedDeltaGlucoseEffect"])
for bIndex in range(len(basalData)):
    print(bIndex)

    basalStartTime = pd.to_datetime(basalData["est.localTime"][bIndex]).round("5min")
    basalRate = basalData["rate"][bIndex]
    durationMilliSeconds = basalData["duration"][bIndex]

    if durationMilliSeconds > 0:

        indBasalEffect = get_basal_insulin_effect(basalStartTime=basalStartTime,
                                                  basalRate=basalRate,
                                                  durationMilliSeconds=durationMilliSeconds,
                                                  pumpModel=pumpModel,
                                                  insulinModel=insulinModel)

        combinedInsulinEffect = pd.concat([combinedInsulinEffect, indBasalEffect[["dateTime", "iob", "normalizedDeltaGlucoseEffect"]]])

        # show the basal rectangle
        if bIndex < (len(basalData) - 1):
            rect = mpatches.Rectangle((basalData.deliveryTimeHoursRelativeToFirstDelivery[bIndex], 0),
                     (basalData.duration[bIndex] / (1000 * 3600)),
                     basalData.rate[bIndex], linewidth=1, edgecolor="#f09a37", facecolor="#f6cc89")

            ax.add_patch(rect)

# combine the effects
dateTimeGroups = combinedInsulinEffect.groupby("dateTime")
basalInsulinEffect = dateTimeGroups.sum()

basalInsulinEffect["normalizedCumulativeGlucoseEffect"] = \
    basalInsulinEffect["normalizedDeltaGlucoseEffect"].cumsum()

basalInsulinEffect["minutesSinceBasalStart"] = np.arange(0, len(basalInsulinEffect) * 5, 5)
basalInsulinEffect["hoursSinceBasalDelivery"] = basalInsulinEffect["minutesSinceBasalStart"] / 60

# plot the curve
ax.plot(basalInsulinEffect.hoursSinceBasalDelivery,
        basalInsulinEffect.iob, lw=4, color="#f09a37")

# run the common figure elements here
ax = common_figure_elements(ax, xLabel, yLabel, figureFont, labelFontSize, tickLabelFontSize, coord_color)

# extras for this plot
ax.set_xlim(-0.1, np.ceil(basalData.deliveryTimeHoursRelativeToFirstDelivery.max()))

# %% make plot of delta BG
figureName = "basal-insulin-effect-delta-BG"
yLabel = "Expected Change (5 minute intervals)"
fig, ax = plt.subplots(figsize=figureSizeInches)
ax.plot(basalInsulinEffect.hoursSinceBasalDelivery,
        basalInsulinEffect.normalizedDeltaGlucoseEffect, lw=4, color="#f09a37")

ax = common_figure_elements(ax, xLabel, yLabel, figureFont, labelFontSize, tickLabelFontSize, coord_color)

# extras for this plot
ax.set_xlim(-0.1, np.ceil(basalData.deliveryTimeHoursRelativeToFirstDelivery.max()))
