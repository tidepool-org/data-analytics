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


# %% build linear regression function that mimics loop
#def linear_regression(last4CgmTimes, last4CgmValues):
#
#    count = len(last4CgmValues)
#
#    sumX = np.sum(last4CgmTimes)
#    sumY = np.sum(last4CgmValues)
#    sumXY = np.sum(last4CgmTimes * last4CgmValues)
#    sumX2 = np.sum(last4CgmTimes * last4CgmTimes)
#    #sumY2 = (last4CgmValues * last4CgmValues)
#
#    slope = ((count * sumXY) - (sumX * sumY)) / ((count * sumX2) - (sumX * sumX))
##    pdb.set_trace()
#    #intercept = (sumY * sumX2 - (sumX * sumXY)) / (count * sumX2 - (sumX * sumX))
#
##    func linearRegression() -> (slope: Double, intercept: Double) {
##        var sumX = 0.0
##        var sumY = 0.0
##        var sumXY = 0.0
##        var sumX² = 0.0
##        var sumY² = 0.0
##        let count = Double(self.count)
##
##        for point in self {
##            sumX += point.x
##            sumY += point.y
##            sumXY += (point.x * point.y)
##            sumX² += (point.x * point.x)
##            sumY² += (point.y * point.y)
##        }
##
##        let slope = ((count * sumXY) - (sumX * sumY)) / ((count * sumX²) - (sumX * sumX))
##        let intercept = (sumY * sumX² - (sumX * sumXY)) / (count * sumX² - (sumX * sumX))
##
##        return (slope: slope, intercept: intercept)
#
#
#
#
#
#    return slope
#
#
#def bg_momentum(last4CgmTimes, last4CgmValues):
#
#    bgSlope = linear_regression(last4CgmTimes, last4CgmValues)
#    print(bgSlope)
#
#    timeSinceNow = np.arange(0, 25, 5)
#    predictedTime = timeSinceNow + last4CgmTimes[-1]
#    predictedCgm = last4CgmValues[-1] + (timeSinceNow * bgSlope)
##    pdb.set_trace()
#
#    return predictedTime, predictedCgm


# %% specify the CGM Data (in minutes and mg/dL)
#cgmTimes = np.array([5, 120, 240, 360])
#cgmValues = np.array([100, 95, 115, 200])
#
#simulatedTime, simulatedCgm = simulate_cgm_data(cgmTimes, cgmValues, amountOfWiggle=3)
#
#predictedTime, predictedCgm = bg_momentum(simulatedTime[-3:], simulatedCgm[-3:])




# %% the blended effect

#2018-12-13 22:30:18 +0000, quantity: 69 mg/dL
#2018-12-13 22:35:17 +0000, quantity: 93 mg/dL
#2018-12-13 22:40:17 +0000, quantity: 116 mg/dL


# * PredictedGlucoseValue(start, mg/dL)
#* 2018-12-06 12:40:41 +0000, 87.0
#* 2018-12-06 12:45:00 +0000, 85.70684058814699
#* 2018-12-06 12:50:00 +0000, 84.65115699114517
#* 2018-12-06 12:55:00 +0000, 84.11289977213242
#* 2018-12-06 13:00:00 +0000, 84.09347477130841
#* 2018-12-06 13:05:00 +0000, 84.14728326553768
#
#[LoopKit.GlucoseEffect(startDate: 2018-12-06 12:40:00 +0000, quantity: 87 mg/dL),
# LoopKit.GlucoseEffect(startDate: 2018-12-06 12:45:00 +0000, quantity: 86.9773 mg/dL),
# LoopKit.GlucoseEffect(startDate: 2018-12-06 12:50:00 +0000, quantity: 86.9567 mg/dL),
# LoopKit.GlucoseEffect(startDate: 2018-12-06 12:55:00 +0000, quantity: 86.9381 mg/dL),
# LoopKit.GlucoseEffect(startDate: 2018-12-06 13:00:00 +0000, quantity: 86.9216 mg/dL),
# LoopKit.GlucoseEffect(startDate: 2018-12-06 13:05:00 +0000, quantity: 86.9072 mg/dL),
# LoopKit.GlucoseEffect(startDate: 2018-12-06 13:10:00 +0000, quantity: 86.8948 mg/dL),
# LoopKit.GlucoseEffect(startDate: 2018-12-06 13:15:00 +0000, quantity: 86.8845 mg/dL),
# LoopKit.GlucoseEffect(startDate: 2018-12-06 13:20:00 +0000, quantity: 86.8762 mg/dL),
# LoopKit.GlucoseEffect(startDate: 2018-12-06 13:25:00 +0000, quantity: 86.87 mg/dL),
# LoopKit.GlucoseEffect(startDate: 2018-12-06 13:30:00 +0000, quantity: 86.8659 mg/dL),
# LoopKit.GlucoseEffect(startDate: 2018-12-06 13:35:00 +0000, quantity: 86.8639 mg/dL),
# LoopKit.GlucoseEffect(startDate: 2018-12-06 13:40:00 +0000, quantity: 86.8639 mg/dL)]


## set up some example data
#effectValuesAtDate = np.array([  0,  -3,  -3,  -3, -3])
#exampleCgmTime = np.array([345.3, 350.3, 355.2833333333333333, 360.2833333333333333])
#exampleCgmData = np.array([64, 69, 93, 116])
#startingGlucose = 360.2833333333333333
#startingGlucoseValue = 116
#
#momentumTime, momentum = bg_momentum(exampleCgmTime, exampleCgmData)
#
#previousEffectValue = momentum[0]
#blendCount = len(momentum) - 2
#timeDelta = (momentumTime[1] - momentumTime[0])
#momentumOffset = startingGlucose - momentumTime[0]
#blendSlope = 1.0 / blendCount
#blendOffset = momentumOffset / timeDelta * blendSlope
#
#newEffectValuesAtDate = np.array([])
#newEffectBG = np.array([])
#for index, effect, effectTime in zip(np.arange(len(momentum)), momentum, momentumTime):
#    value = effect
#    effectValueChange = value - previousEffectValue
##    print(effectValueChange)
#    split = min(1.0, max(0.0, ((len(momentum) - index) / blendCount) - blendSlope + blendOffset))
##    print(split)
#    effectBlend = (1.0 - split) * (effectValuesAtDate[index])
#    momentumBlend = split * effectValueChange
##    print(momentumBlend)
#    newEffectValuesAtDate = np.append(newEffectValuesAtDate, effectBlend + momentumBlend)
#    newEffectBG = np.append(newEffectBG, startingGlucoseValue + newEffectValuesAtDate[index])
#    startingGlucoseValue = newEffectBG[index]
#    previousEffectValue = value


# %% testing the linear regression

#▿ 3 elements
#  ▿ 0 : GlucoseFixtureValue
#    ▿ startDate : 2015-10-26 01:19:37 +0000
#      - timeIntervalSinceReferenceDate : 467515177.0
#    - quantity : 123 mg/dL
#    - isDisplayOnly : false
#    - provenanceIdentifier : "com.loopkit.LoopKitTests"
#  ▿ 1 : GlucoseFixtureValue
#    ▿ startDate : 2015-10-26 01:24:36 +0000
#      - timeIntervalSinceReferenceDate : 467515476.0
#    - quantity : 120 mg/dL
#    - isDisplayOnly : false
#    - provenanceIdentifier : "com.loopkit.LoopKitTests"
#  ▿ 2 : GlucoseFixtureValue
#    ▿ startDate : 2015-10-26 01:29:37 +0000
#      - timeIntervalSinceReferenceDate : 467515777.0
#    - quantity :  mg/dL
#    - isDisplayOnly : false
#    - provenanceIdentifier : "com.loopkit.LoopKitTests"

#▿ 8 elements
#  ▿ 0 : GlucoseEffect
#    ▿ startDate : 2015-10-26 01:25:00 +0000
#      - timeIntervalSinceReferenceDate : 467515500.0
#    - quantity : 0 mg/dL
#  ▿ 1 : GlucoseEffect
#    ▿ startDate : 2015-10-26 01:30:00 +0000
#      - timeIntervalSinceReferenceDate : 467515800.0
#    - quantity : 0.23051 mg/dL
#  ▿ 2 : GlucoseEffect
#    ▿ startDate : 2015-10-26 01:35:00 +0000
#      - timeIntervalSinceReferenceDate : 467516100.0
#    - quantity : 3.23717 mg/dL
#  ▿ 3 : GlucoseEffect
#    ▿ startDate : 2015-10-26 01:40:00 +0000
#      - timeIntervalSinceReferenceDate : 467516400.0
#    - quantity : 6.24382 mg/dL
#  ▿ 4 : GlucoseEffect
#    ▿ startDate : 2015-10-26 01:45:00 +0000
#      - timeIntervalSinceReferenceDate : 467516700.0
#    - quantity : 9.25048 mg/dL
#  ▿ 5 : GlucoseEffect
#    ▿ startDate : 2015-10-26 01:50:00 +0000
#      - timeIntervalSinceReferenceDate : 467517000.0
#    - quantity : 12.2571 mg/dL
#  ▿ 6 : GlucoseEffect
#    ▿ startDate : 2015-10-26 01:55:00 +0000
#      - timeIntervalSinceReferenceDate : 467517300.0
#    - quantity : 15.2638 mg/dL
#  ▿ 7 : GlucoseEffect
#    ▿ startDate : 2015-10-26 02:00:00 +0000
#      - timeIntervalSinceReferenceDate : 467517600.0
#    - quantity : 18.2704 mg/dL

def linear_regression(cgmTimesSeconds, cgmValues):

    count = len(cgmValues)

    sumX = np.sum(cgmTimesSeconds)
    sumY = np.sum(cgmValues)
    sumXY = np.sum(cgmTimesSeconds * cgmValues)
    sumX2 = np.sum(cgmTimesSeconds * cgmTimesSeconds)
    #sumY2 = (cgmValues * cgmValues)

    slope = ((count * sumXY) - (sumX * sumY)) / ((count * sumX2) - (sumX * sumX))
    #intercept = (sumY * sumX2 - (sumX * sumXY)) / (count * sumX2 - (sumX * sumX))

    return slope


def momenutum_effect(exampleCgmTime, exampleCgmData):

    bgSlope = linear_regression(exampleCgmTime, exampleCgmData)

    # key point is that simluation date range rounds start times down and end times up to the nearest 5 minutes
    durationMinutes = 15  # leaving this hard coded for now
    deltaMinutes = 5  # leaving this hard coded for now
    durationSeconds = durationMinutes * 60
    deltaSeconds = deltaMinutes * 60
    startDate = np.floor(exampleCgmTime[-1]/300) * 300
    endDate = np.ceil((exampleCgmTime[-1] + durationSeconds + deltaSeconds) / 300) * 300
    simulationDateRange = np.arange(startDate, endDate + 300, 300)

    timeIntervalSinceLastCgm = simulationDateRange - exampleCgmTime[-1]
    # make all negative time deltas 0
    timeIntervalSinceLastCgm[timeIntervalSinceLastCgm < 0] = 0

    momentum = timeIntervalSinceLastCgm * bgSlope

    return simulationDateRange, momentum, bgSlope

exampleCgmTime = np.array([467515177, 467515476, 467515777])
exampleCgmData = np.array([123, 120, 129])

momentumTime, momentum, slope  = momenutum_effect(exampleCgmTime, exampleCgmData)

# %% test the blending effect using the xcode test case


#▿ PredictedGlucoseValue
#  ▿ startDate : 2015-10-30 15:17:27 +0000
#    - timeIntervalSinceReferenceDate : 467911047.0
#  - quantity : 111 mg/dL

#Printing description of momentum:
#▿ 5 elements
#  ▿ 0 : GlucoseEffect
#    ▿ startDate : 2015-10-30 15:15:00 +0000
#      - timeIntervalSinceReferenceDate : 467910900.0
#    - quantity : -0 mg/dL
#  ▿ 1 : GlucoseEffect
#    ▿ startDate : 2015-10-30 15:20:00 +0000
#      - timeIntervalSinceReferenceDate : 467911200.0
#    - quantity : -0.51 mg/dL
#  ▿ 2 : GlucoseEffect
#    ▿ startDate : 2015-10-30 15:25:00 +0000
#      - timeIntervalSinceReferenceDate : 467911500.0
#    - quantity : -1.51 mg/dL
#  ▿ 3 : GlucoseEffect
#    ▿ startDate : 2015-10-30 15:30:00 +0000
#      - timeIntervalSinceReferenceDate : 467911800.0
#    - quantity : -2.51 mg/dL
#  ▿ 4 : GlucoseEffect
#    ▿ startDate : 2015-10-30 15:35:00 +0000
#      - timeIntervalSinceReferenceDate : 467912100.0
#    - quantity : -3.51 mg/dL

# Printing description of insulinEffect:
#▿ 7 elements
#  ▿ 0 : GlucoseEffect
#    ▿ startDate : 2015-10-30 15:15:00 +0000
#      - timeIntervalSinceReferenceDate : 467910900.0
#    - quantity : -96.6443 mg/dL
#  ▿ 1 : GlucoseEffect
#    ▿ startDate : 2015-10-30 15:20:00 +0000
#      - timeIntervalSinceReferenceDate : 467911200.0
#    - quantity : -96.919 mg/dL
#  ▿ 2 : GlucoseEffect
#    ▿ startDate : 2015-10-30 15:25:00 +0000
#      - timeIntervalSinceReferenceDate : 467911500.0
#    - quantity : -97.1471 mg/dL
#  ▿ 3 : GlucoseEffect
#    ▿ startDate : 2015-10-30 15:30:00 +0000
#      - timeIntervalSinceReferenceDate : 467911800.0
#    - quantity : -97.3095 mg/dL
#  ▿ 4 : GlucoseEffect
#    ▿ startDate : 2015-10-30 15:35:00 +0000
#      - timeIntervalSinceReferenceDate : 467912100.0
#    - quantity : -97.4078 mg/dL
#  ▿ 5 : GlucoseEffect
#    ▿ startDate : 2015-10-30 15:40:00 +0000
#      - timeIntervalSinceReferenceDate : 467912400.0
#    - quantity : -97.447 mg/dL
#  ▿ 6 : GlucoseEffect
#    ▿ startDate : 2015-10-30 15:45:00 +0000
#      - timeIntervalSinceReferenceDate : 467912700.0
#    - quantity : -97.4284 mg/dL



#▿ 7 elements
#  ▿ 0 : PredictedGlucoseValue
#    ▿ startDate : 2015-10-30 15:17:27 +0000
#      - timeIntervalSinceReferenceDate : 467911047.0
#    - quantity : 111 mg/dL
#  ▿ 1 : PredictedGlucoseValue
#    ▿ startDate : 2015-10-30 15:20:00 +0000
#      - timeIntervalSinceReferenceDate : 467911200.0
#    - quantity : 110.49 mg/dL
#  ▿ 2 : PredictedGlucoseValue
#    ▿ startDate : 2015-10-30 15:25:00 +0000
#      - timeIntervalSinceReferenceDate : 467911500.0
#    - quantity : 109.621 mg/dL
#  ▿ 3 : PredictedGlucoseValue
#    ▿ startDate : 2015-10-30 15:30:00 +0000
#      - timeIntervalSinceReferenceDate : 467911800.0
#    - quantity : 109.043 mg/dL
#  ▿ 4 : PredictedGlucoseValue
#    ▿ startDate : 2015-10-30 15:35:00 +0000
#      - timeIntervalSinceReferenceDate : 467912100.0
#    - quantity : 108.797 mg/dL
#  ▿ 5 : PredictedGlucoseValue
#    ▿ startDate : 2015-10-30 15:40:00 +0000
#      - timeIntervalSinceReferenceDate : 467912400.0
#    - quantity : 108.758 mg/dL
#  ▿ 6 : PredictedGlucoseValue
#    ▿ startDate : 2015-10-30 15:45:00 +0000
#      - timeIntervalSinceReferenceDate : 467912700.0
#    - quantity : 108.777 mg/dL

momentum = np.array([0, -0.51, -1.51, -2.51, -3.51])
momentumTime = np.array([467910900, 467911200, 467911500, 467911800, 467912100])
insulinEffect = np.array([-96.6443, -96.919, -97.1471, -97.3095, -97.4078, -97.447, -97.4284])  # comes from insulin effect example
insulinEffectTime = np.array([467910900, 467911200, 467911500, 467911800, 467912100, 467912400, 467912700])
startingGlucoseValue = np.array([111])
startingGlucoseTime = np.array([467910900.])

# the insulin effect OR the other effects need to get processed first
effectValues = []
previousEffectValue = insulinEffect[0]
for effect in insulinEffect:
    value = effect
    effectValueChange = value - previousEffectValue
    effectValues = np.append(effectValues, value - previousEffectValue)
    previousEffectValue = value

# then the blended effect
previousEffectValue = momentum[0]
blendCount = len(momentum) - 2
timeDelta = (momentumTime[1] - momentumTime[0])
momentumOffset = startingGlucoseTime - momentumTime[0]
blendSlope = 1.0 / blendCount
blendOffset = momentumOffset / timeDelta * blendSlope

neweffectValues = np.array([])
newEffectBG = np.array([])

for index, effect, effectTime in zip(np.arange(len(momentum)), momentum, momentumTime):
    value = effect
    effectValueChange = value - previousEffectValue
#    print(effectValueChange)
    split = min(1.0, max(0.0, ((len(momentum) - index) / blendCount) - blendSlope + blendOffset))
    print(split)
    effectBlend = (1.0 - split) * (effectValues[index])
    momentumBlend = split * effectValueChange
#    print(momentumBlend)
    neweffectValues = np.append(neweffectValues, effectBlend + momentumBlend)
#    print(effectBlend, momentumBlend)
    newEffectBG = np.append(newEffectBG, startingGlucoseValue + neweffectValues[index])
    startingGlucoseValue = newEffectBG[index]
    previousEffectValue = value

# %% VERY NEXT ACTION IS TO MAKE A FEW FIGURES TO DEMONSTRATE THE EFFECT








# %% define the insulin model and number of insulin boluses
#
## two insulin boluses example
#figureClass = "LoopOverview-EffectTwoInsulinBolusesV" + str(versionNumber) + "-"
#
#insulinModel = "humalogNovologAdult"
#peakActivityTime = 60
#activeDuration = 6
#isf = 50
#
#currentTime = dt.datetime.now()
#
## update this array to include when you want the insulin boluses to occer
#deliveryTimeHoursRelativeToFirstDelivery = [0, 3]  # in hours
#insulinAmount = [2, 3]
#
#deliveryTime = list(map(lambda i: currentTime + pd.Timedelta(i, unit="h"), deliveryTimeHoursRelativeToFirstDelivery))
#for bolusNumber in range(len(insulinAmount)):
#    insulinEffect = get_insulin_effect(model=insulinModel,
#                                       peakActivityTime=peakActivityTime,
#                                       activeDuration=activeDuration,
#                                       deliveryTime=deliveryTime[bolusNumber],
#                                       insulinAmount=insulinAmount[bolusNumber],
#                                       isf=isf)
#    # append rows of insulinEffect into the cumulativeEffect
#    if bolusNumber > 0:
#        tempEffect = pd.concat([tempEffect, insulinEffect])
#    else:
#        tempEffect = insulinEffect.copy()
#
## take all of the insulin boluses and combine (add the effects)
#dateTimeGroups = tempEffect.groupby("dateTime")
#cumulativeInsulinEffect = dateTimeGroups.sum().reset_index(drop=False)
## drop the insulin on board percentage as it no longer has meaning
#cumulativeInsulinEffect.drop(columns=["iobPercent", "minutesSinceDelivery"], inplace=True)
#
## add a column minutesSinceFirstDelivery
#cumulativeInsulinEffect["minutesSinceFirstDelivery"] = \
#    np.arange(0, len(cumulativeInsulinEffect)* 5, 5)
#
## recalculate the cumulative effect of BG
#cumulativeInsulinEffect["cumulativeGlucoseEffect"] = \
#    cumulativeInsulinEffect["deltaGlucoseEffect"].cumsum()
#
#xData = cumulativeInsulinEffect["minutesSinceFirstDelivery"]/60
#
#
## %% iob
#figureName = "iob-amount"
#yLabel = "Insulin-On-Board (U)"
#fig, ax = plt.subplots(figsize=figureSizeInches)
#
## fill the area under the curve with light orange
#ax.fill_between(xData, 0, cumulativeInsulinEffect["iob"], color="#f6cc89")
#
## plot the curve
#ax.plot(xData, cumulativeInsulinEffect["iob"], lw=4, color="#f09a37")
#
## run the common figure elements here
#ax = common_figure_elements(ax, xLabel, yLabel, figureFont, labelFontSize, tickLabelFontSize, coord_color)
#
## show the insulin delivered
#for bolusNumber in range(len(insulinAmount)):
#    ax.plot(deliveryTimeHoursRelativeToFirstDelivery[bolusNumber],
#            cumulativeInsulinEffect.loc[int(deliveryTimeHoursRelativeToFirstDelivery[bolusNumber] * 60 / 5), "iob"] + 0.15,
#            marker='v', markersize=16, color="#f09a37",
#            ls="None", label="%d Units of Insulin Delivered" % insulinAmount[bolusNumber])
#
#    ax.text(deliveryTimeHoursRelativeToFirstDelivery[bolusNumber],
#            cumulativeInsulinEffect.loc[int(deliveryTimeHoursRelativeToFirstDelivery[bolusNumber] * 60 / 5), "iob"] + 0.3,
#            "%d Units Delivered" % insulinAmount[bolusNumber],
#            horizontalalignment="left", fontproperties=figureFont, size=labelFontSize, color=coord_color)
#
#
#plt.xlim([min(xData) - 0.1, max(xData)])
## save the figure
#plt.savefig(os.path.join(outputPath, figureClass + figureName + ".png"))
#plt.show()
#plt.close('all')
#
#
## %% delta BG
#figureName = "delta-bg"
#yLabel = "Change in BG (mg/dL) every 5 minutes"
#fig, ax = plt.subplots(figsize=figureSizeInches)
#
## plot the curve
#ax.scatter(xData, cumulativeInsulinEffect["deltaGlucoseEffect"], color="#f09a37")
#
## run the common figure elements here
#ax = common_figure_elements(ax, xLabel, yLabel, figureFont, labelFontSize, tickLabelFontSize, coord_color)
#
#
## show the insulin delivered
#for bolusNumber in range(len(insulinAmount)):
#    ax.plot(deliveryTimeHoursRelativeToFirstDelivery[bolusNumber],
#            cumulativeInsulinEffect.loc[int(deliveryTimeHoursRelativeToFirstDelivery[bolusNumber] * 60 / 5), "deltaGlucoseEffect"] + 0.2,
#            marker='v', markersize=16, color="#f09a37",
#            ls="None", label="%d Units of Insulin Delivered" % insulinAmount[bolusNumber])
#
#    ax.text(deliveryTimeHoursRelativeToFirstDelivery[bolusNumber] + 0.1,
#            cumulativeInsulinEffect.loc[int(deliveryTimeHoursRelativeToFirstDelivery[bolusNumber] * 60 / 5), "deltaGlucoseEffect"] + 0.1,
#            "%d Units Delivered" % insulinAmount[bolusNumber],
#            horizontalalignment="left", fontproperties=figureFont, size=labelFontSize, color=coord_color)
#
#
## extras for this plot
#ax.set_xlim(-0.1, 10)
#
## save the figure
#plt.savefig(os.path.join(outputPath, figureClass + figureName + ".png"))
#plt.show()
#plt.close('all')
#
#
## %% cumulative glucose effect
#figureName = "cumulative-insulin-effect"
#yLabel = "Cumulative Insulin Effect on BG (mg/dL)"
#fig, ax = plt.subplots(figsize=figureSizeInches)
#
## plot the curve
#ax.plot(xData, cumulativeInsulinEffect["cumulativeGlucoseEffect"], lw=4, color="#f09a37")
#
## run the common figure elements here
#ax = common_figure_elements(ax, xLabel, yLabel, figureFont, labelFontSize, tickLabelFontSize, coord_color)
#
## extras for this plot
#ax.set_xlim(-0.1, 10)
#
## show the insulin delivered
#for bolusNumber in range(len(insulinAmount)):
#    ax.plot(deliveryTimeHoursRelativeToFirstDelivery[bolusNumber],
#            cumulativeInsulinEffect.loc[int(deliveryTimeHoursRelativeToFirstDelivery[bolusNumber] * 60 / 5), "cumulativeGlucoseEffect"],
#            marker='v', markersize=16, color="#f09a37",
#            ls="None", label="%d Units of Insulin Delivered" % insulinAmount[bolusNumber])
#
#    ax.text(deliveryTimeHoursRelativeToFirstDelivery[bolusNumber] + 0.1,
#            cumulativeInsulinEffect.loc[int(deliveryTimeHoursRelativeToFirstDelivery[bolusNumber] * 60 / 5), "cumulativeGlucoseEffect"] + 5,
#            "%d Units Delivered" % insulinAmount[bolusNumber],
#            horizontalalignment="left", fontproperties=figureFont, size=labelFontSize, color=coord_color)
#
#
## save the figure
#plt.savefig(os.path.join(outputPath, figureClass + figureName + ".png"))
#plt.show()
#plt.close('all')
#
#
## %% now show example with the previous plot
## specify the time you want the simulation to start
#startTimeHour = 6
#startTimeAMPM = "AM"
#
### %% apply the insulin effect
#predictedTime = np.arange(0, len(cumulativeInsulinEffect) * 5, 5)
#predictedCgm = 355 + np.round(cumulativeInsulinEffect["cumulativeGlucoseEffect"].values)
#
## specify the CGM Data (in minutes and mg/dL)
#cgmTimes =  predictedTime[range(0, 45, 9)]
#cgmValues = predictedCgm[range(0, 45, 9)]
#simulatedTime, simulatedCgm = simulate_cgm_data(cgmTimes, cgmValues, amountOfWiggle=3)
#
### %% filter the predicted time to NOT overlap with the cgm data
#predictedTime = predictedTime[37:110]
#predictedCgm = predictedCgm[37:110]
#
## make the figure
#figureName = "insulin-effect-example"
#fig, ax = plt.subplots(figsize=figureSizeInches)
#plt.ylim((80, 400))
#yLabel = "Glucose (mg/dL)"
#
## plot correction range
#correction_min = 90
#correction_max = 120
#
## plot correction range
#ax.fill_between(np.arange(0, (len(simulatedCgm) + len(predictedCgm)) * 5, 5),
#                correction_min,
#                correction_max,
#                facecolor='#bde5fc', lw=0)
#
#ax.plot([], [], color='#bde5fc', linewidth=10,
#        label="Correction Range: %d-%d" % (correction_min, correction_max))
#
#
#
#
## plot predicted cgm
#ax.plot(predictedTime, predictedCgm, linestyle="--", color="#4faef8", lw=4, label="Prediction (Insulin Effect Only)")
#
## plot the current time
#ax.plot(simulatedTime[-1], simulatedCgm[-1],
#        marker='*', markersize=16, color=coord_color, markeredgecolor = "black", alpha=0.5,
#        ls="None", label="Current Time")
#
### plot eventual bg
##ax.plot(predictedTime[-1], predictedCgm[-1],
##        marker='*', markersize=16, color="#4faef8",
##        ls="None", label="Eventual BG = %d" % predictedCgm[-1])
#
## plot simulated cgm
#ax.scatter(simulatedTime, simulatedCgm, s=18, color="#4faef8", label="CGM Data")
#
## define the legend
#leg = plt.legend(scatterpoints=3, edgecolor="black")
#for text in leg.get_texts():
#    text.set_color('#606060')
#    text.set_weight('normal')
#
## show the insulin delivered
#for bolusNumber in range(len(insulinAmount)):
#    ax.plot(deliveryTimeHoursRelativeToFirstDelivery[bolusNumber] * 60,
#            cumulativeInsulinEffect.loc[int(deliveryTimeHoursRelativeToFirstDelivery[bolusNumber] * 60 / 5), "cumulativeGlucoseEffect"] + 370,
#            marker='v', markersize=16, color="#f09a37",
#            ls="None", label="%d Units of Insulin Delivered" % insulinAmount[bolusNumber])
#
#    ax.text(deliveryTimeHoursRelativeToFirstDelivery[bolusNumber] * 60 + 10,
#            cumulativeInsulinEffect.loc[int(deliveryTimeHoursRelativeToFirstDelivery[bolusNumber] * 60 / 5), "cumulativeGlucoseEffect"] + 365,
#            "%d Units Delivered" % insulinAmount[bolusNumber],
#            horizontalalignment="left", fontproperties=figureFont, size=labelFontSize, color=coord_color)
#
#
## run the common figure elements here
#ax = common_figure_elements(ax, xLabel, yLabel, figureFont, labelFontSize, tickLabelFontSize, coord_color, yLabel_xOffset=50)
#
## extras for this plot
#ax.set_xlabel("")
#plt.xlim([min(simulatedTime) - 15, max(predictedTime) + 15])
#ax.text(max(ax.get_xlim()),
#        max(ax.get_ylim()) + 7,
#        "Eventually %d mg/dL" % predictedCgm[-1],
#        horizontalalignment="right", fontproperties=figureFont, size=labelFontSize, color=coord_color)
#
## set tick marks
#minuteTicks = np.arange(0, (len(simulatedTime) + len(predictedTime)) * 5 + 1, 60)
#hourTicks = np.int64(minuteTicks / 60)
#hourLabels = make_hour_labels(startTimeHour, startTimeAMPM, hourTicks)
#ax.set_xticks(minuteTicks)
#ax.set_xticklabels(hourLabels)
#
#plt.savefig(os.path.join(outputPath, figureClass + figureName + ".png"))
#plt.show()
#plt.close('all')
#
## %%
#
#
#
