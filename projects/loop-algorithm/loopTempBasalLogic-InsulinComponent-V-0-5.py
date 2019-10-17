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
    simulatedCgm = splineFit(simulatedTime)
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


# %% define the exponential model
insulinModel = "humalogNovologAdult"
peakActivityTime = 60
activeDuration = 6
deliveryTime = dt.datetime.now()
insulinAmount = 2
isf = 50

insulinEffect = get_insulin_effect(model=insulinModel,
                                   peakActivityTime=peakActivityTime,
                                   activeDuration=activeDuration,
                                   deliveryTime=deliveryTime,
                                   insulinAmount=insulinAmount,
                                   isf=isf)

xData = insulinEffect["minutesSinceDelivery"]/60


# %% set figure properties
versionNumber = 0
subversionNumber = 4
figureClass = "LoopOverview-InsulinEffect" + "-" + \
    "V" + str(versionNumber) + "-" +str(subversionNumber)
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

xLabel = "Time Since Delivery (Hours)"
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


# %%iob percentage
figureName = "iob-percentage"
yLabel = "Insulin-On-Board (%)"
fig, ax = plt.subplots(figsize=figureSizeInches)

# fill the area under the curve with light orange
ax.fill_between(xData, 0, insulinEffect["iobPercent"] * 100, color="#f6cc89")

# plot the curve
ax.plot(xData, insulinEffect["iobPercent"] * 100, lw=4, color="#f09a37")

# run the common figure elements here
ax = common_figure_elements(ax, xLabel, yLabel, figureFont, labelFontSize, tickLabelFontSize, coord_color)

# save the figure
plt.savefig(os.path.join(outputPath, figureClass + figureName + ".png"))
plt.show()
plt.close('all')


# %% iob
figureName = "iob-amount"
yLabel = "Insulin-On-Board (U)"
fig, ax = plt.subplots(figsize=figureSizeInches)

# fill the area under the curve with light orange
ax.fill_between(xData, 0, insulinEffect["iob"], color="#f6cc89")

# plot the curve
ax.plot(xData, insulinEffect["iob"], lw=4, color="#f09a37")

# run the common figure elements here
ax = common_figure_elements(ax, xLabel, yLabel, figureFont, labelFontSize, tickLabelFontSize, coord_color)

# save the figure
plt.savefig(os.path.join(outputPath, figureClass + figureName + ".png"))
plt.show()
plt.close('all')


# %% delta BG
figureName = "delta-bg"
yLabel = "Change in BG (mg/dL) every 5 minutes"
fig, ax = plt.subplots(figsize=figureSizeInches)

# plot the curve
ax.scatter(xData, insulinEffect["deltaGlucoseEffect"], color="#f09a37")

# run the common figure elements here
ax = common_figure_elements(ax, xLabel, yLabel, figureFont, labelFontSize, tickLabelFontSize, coord_color)

# extras for this plot
ax.set_xlim(-0.025, 8)

# save the figure
plt.savefig(os.path.join(outputPath, figureClass + figureName + ".png"))
plt.show()
plt.close('all')


# %% cumulative glucose effect
figureName = "cumulative-insulin-effect"
yLabel = "Cumulative Insulin Effect on BG (mg/dL)"
fig, ax = plt.subplots(figsize=figureSizeInches)

# plot the curve
ax.plot(xData, insulinEffect["cumulativeGlucoseEffect"], lw=4, color="#f09a37")

# run the common figure elements here
ax = common_figure_elements(ax, xLabel, yLabel, figureFont, labelFontSize, tickLabelFontSize, coord_color)

# save the figure
plt.savefig(os.path.join(outputPath, figureClass + figureName + ".png"))
plt.show()
plt.close('all')


# %% now show example with the previous plot

# specify the CGM Data (in minutes and mg/dL)
cgmTimes =  [5,    60, 120, 180, 240, 300, 345, 360]
cgmValues = [100, 140, 180, 200, 210, 195, 205, 205]
simulatedTime, simulatedCgm = simulate_cgm_data(cgmTimes, cgmValues, amountOfWiggle=2)

# specify the time you want the simulation to start
startTimeHour = 6
startTimeAMPM = "AM"

## %% apply the insulin effect
predictedTime = np.arange(360, 725, 5)
predictedCgm = 205 + (insulinEffect["cumulativeGlucoseEffect"][0:73].values)

## make the figure
#figureName = "insulin-effect-example"
#fig, ax = plt.subplots(figsize=figureSizeInches)
#plt.ylim((80, 220))
yLabel = "Glucose (mg/dL)"

# plot correction range
correction_min = 90
correction_max = 120
#
## plot correction range
#ax.fill_between(np.arange(0, 725, 5),
#                correction_min,
#                correction_max,
#                facecolor='#B5E7FF', lw=0)
#
#ax.plot([], [], color='#B5E7FF', linewidth=10,
#        label="Correction Range: %d-%d" % (correction_min, correction_max))
#
## plot predicted cgm
#ax.plot(predictedTime, predictedCgm, linestyle="--", color="#31B0FF", lw=1, label="Prediction (Insulin Effect Only)")
#
#        # plot simulated cgm
#ax.scatter(simulatedTime, simulatedCgm, s=10, color="#31B0FF", label="CGM Data")
#
#
## show the insulin delivered
#ax.plot(predictedTime[0] - 5, predictedCgm[0] + 5,
#        marker='v', markersize=16, color="#f09a37",
#        ls="None", label="%d Units of Insulin Delivered" % insulinAmount)
#
#
## plot eventual bg
#ax.plot(predictedTime[-1], predictedCgm[-1],
#        marker='*', markersize=16, color="#4faef8",
#        ls="None", label="Eventual BG = %d" % predictedCgm[-1])
#
#
## define the legend
#leg = plt.legend(scatterpoints=3, edgecolor="black")
#for text in leg.get_texts():
#    text.set_color('#606060')
#    text.set_weight('normal')
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


# new format
figureName = "insulin-effect-example"
fig, ax = plt.subplots(figsize=figureSizeInches)
bgRange = (80, 220)
plt.ylim(bgRange)
ax.set_xlim([min(simulatedTime) - 5, max(predictedTime) + 15])

# show the insulin delivered
ax.plot(predictedTime[0], predictedCgm[0] + 7.5,
        marker='v', markersize=14, color="#f09a37",
        ls="None", label="%d Units of Insulin Delivered" % insulinAmount)

# plot correction range
ax.fill_between([ax.get_xlim()[0], ax.get_xlim()[1]],
                [correction_min, correction_min],
                [correction_max, correction_max],
                facecolor='#B5E7FF', lw=0)

ax.plot([], [], color='#B5E7FF', linewidth=10,
        label="Correction Range = %d - %d" % (correction_min, correction_max))

# plot predicted cgm
ax.plot(predictedTime, predictedCgm, linestyle="--", color="#f09a37", lw=2, label="Predicted Glucose (Insulin Effect Only)")

# plot simulated cgm
ax.scatter(simulatedTime, simulatedCgm, s=10, color="#31B0FF", label="CGM Data")

## plot the Correction Target
#ax.plot(predictedTime[-1], correction_target,
#        marker='*', markersize=16, color="purple", alpha=0.5,
#        ls="None", label="Correction Target = %d" % correction_target)

# plot the current time
ax.plot(simulatedTime[-1], simulatedCgm[-1],
        marker='*', markersize=16, color=coord_color, markeredgecolor = "black", alpha=0.5,
        ls="None", label="Current Time BG =  %d" % simulatedCgm[-1])

# plot eventual bg
ax.plot(predictedTime[-1], predictedCgm[-1],
        marker='*', markersize=16, color="#31B0FF", alpha=0.5,
        ls="None", label="Eventual BG = %d" % predictedCgm[-1])

## find and plot minimum BG
#min_idx = np.argmin(predictedCgm)
#ax.plot(predictedTime[min_idx], predictedCgm[min_idx],
#        marker='*', markersize=16, color="red", alpha=0.25,
#        ls="None", label="Minimum Predicted BG = %d" % predictedCgm[min_idx])

## plot suspend threshold line
#ax.hlines(suspendThreshold, ax.get_xlim()[0], ax.get_xlim()[1],
#          colors="red", label="Suspend Threshold = %d" % suspendThreshold)

## place holder for the delta vertical line in the legend
#delta = int(predictedCgm[-1] - correction_target)
#ax.plot(-10, 10, ls="None", marker="|", markersize=16, markeredgewidth=6, alpha=0.5,
#        color="purple", label="Delta = %d" % delta)

# run the common figure elements here
ax = common_figure_elements(ax, xLabel, yLabel, figureFont, labelFontSize, tickLabelFontSize, coord_color, yLabel_xOffset=32)

# change the order of the legend items
handles, labels = ax.get_legend_handles_labels()
#pdb.set_trace()
handles = [handles[0], handles[5], handles[3], handles[2], handles[4],
           handles[1]]
labels = [labels[0], labels[5], labels[3], labels[2], labels[4],
          labels[1]]

# format the legend
leg = ax.legend(handles, labels, scatterpoints=3, edgecolor="black", loc=1)
for text in leg.get_texts():
    text.set_color('#606060')
    text.set_weight('normal')

## plot the delta
#ax.vlines(predictedTime[-1] + 10, min([correction_target, predictedCgm[-1]]),
#          max([correction_target, predictedCgm[-1]]), linewidth=6, alpha=0.5, colors="purple")

# set tick marks
minuteTicks = np.arange(0, (len(simulatedTime) + len(predictedTime)) * 5 + 1, 60)
hourTicks = np.int64(minuteTicks / 60)
hourLabels = make_hour_labels(startTimeHour, startTimeAMPM, hourTicks)
ax.set_xticks(minuteTicks)
ax.set_xticklabels(hourLabels)


# extras for this plot
ax.set_xlabel("")
plt.xlim([min(simulatedTime) - 15, max(predictedTime) + 15])
ax.text(max(ax.get_xlim()),
        max(ax.get_ylim()) + 7,
        "Eventually %d mg/dL" % predictedCgm[-1],
        horizontalalignment="right", fontproperties=figureFont, size=labelFontSize, color=coord_color)



plt.savefig(os.path.join(outputPath, figureClass + figureName + ".png"))
plt.show()
plt.close('all')



# %% insulin activity curves
peakActivityTime = 60
activeDuration = 6
deliveryTime = dt.datetime.now()
insulinAmount = 1
isf = 50

humNovAdult = get_insulin_effect(model="humalogNovologAdult",
                                   peakActivityTime=peakActivityTime,
                                   activeDuration=activeDuration,
                                   deliveryTime=deliveryTime,
                                   insulinAmount=insulinAmount,
                                   isf=isf)

xData = humNovAdult["minutesSinceDelivery"]/60

humNovChild = get_insulin_effect(model="humalogNovologChild",
                                 peakActivityTime=peakActivityTime,
                                 activeDuration=activeDuration,
                                 deliveryTime=deliveryTime,
                                 insulinAmount=insulinAmount,
                                 isf=isf)

fiasp = get_insulin_effect(model="fiasp",
                           peakActivityTime=peakActivityTime,
                           activeDuration=activeDuration,
                           deliveryTime=deliveryTime,
                           insulinAmount=insulinAmount,
                           isf=isf)

walsh = get_insulin_effect(model="walsh",
                           peakActivityTime=peakActivityTime,
                           activeDuration=activeDuration,
                           deliveryTime=deliveryTime,
                           insulinAmount=insulinAmount,
                           isf=isf)



# %% first make a plot of just one curve for illustrative purposes
figureName = "insulin-activity-curve-v0-3"
yLabel = "Insulin Absorption (U/hr)"
fig, ax = plt.subplots(figsize=figureSizeInches)

# plot the activty curve by normalizing the delta BG effect
ax.plot(xData, abs(humNovChild["deltaGlucoseEffect"] * 12) / isf,
        color="#f09a37", lw=4, ls="-")


# run the common figure elements here
ax = common_figure_elements(ax, xLabel, yLabel, figureFont, labelFontSize, tickLabelFontSize, coord_color)

# extras for this plot
ax.set_xlim(-0.025, 6)

# save the figure
plt.savefig(os.path.join(outputPath, figureClass + figureName + ".png"))
plt.show()
plt.close('all')


# %% show all of the insulin activity curves on one figure
figureName = "insulin-activity-curves-v0-5"
yLabel = "Insulin Absorption (U/hr)"
fig, ax = plt.subplots(figsize=figureSizeInches)

# plot the activty curve by normalizing the delta BG effect
ax.plot(xData, abs(humNovChild["deltaGlucoseEffect"] * 12) / isf, color="#f09a37", lw=3, ls="-")
ax.plot(xData, abs(humNovAdult["deltaGlucoseEffect"] * 12) / isf, color="#f09a37", lw=3, ls=":")
#ax.plot(xData, abs(fiasp["deltaGlucoseEffect"] * 12) / isf, color="#f09a37", lw=3, ls="--")
#ax.plot(xData, abs(walsh["deltaGlucoseEffect"] * 12) / isf, color="#f09a37", lw=3, ls="-.")

# run the common figure elements here
ax = common_figure_elements(ax, xLabel, yLabel, figureFont, labelFontSize, tickLabelFontSize, coord_color)

# define the legend
leg = plt.legend(["Rapid-Acting-Child (peak 65 min)",
                  "Rapid-Acting-Adult (peak 75 min)"], edgecolor="black")

#leg = plt.legend(["Rapid-Acting-Child (peak 65 min)",
#                  "Rapid-Acting-Adult (peak 75 min)",
#                  "Rapid-Acting-Fiasp (peak 55 min)",
#                  "Walsh-6hr-Model (peak 140 min)"], edgecolor="black")

for text in leg.get_texts():
    text.set_color('#606060')
    text.set_weight('normal')

# extras for this plot
ax.set_xlim(-0.025, 6.1)

# save the figure
plt.savefig(os.path.join(outputPath, figureClass + figureName + ".png"))
plt.show()
plt.close('all')

