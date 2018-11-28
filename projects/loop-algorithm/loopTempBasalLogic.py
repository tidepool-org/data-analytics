#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: demonstrate the logic of the loop
version: 0.0.1
created: 2018-11-28
author: Ed Nykaza (original credit goes to Pete Schwamb, https://github.com/ps2/LoopExplain/blob/master/Loop%20Explain.ipynb)
license: BSD-2-Clause
"""


# %% required libraries
import os
import numpy as np
import pandas as pd
from scipy.interpolate import BSpline, make_interp_spline
from matplotlib import pyplot as plt
from matplotlib.legend_handler import HandlerLine2D


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


# %% specify the CGM Data (in minutes and mg/dL)
cgmTimes = [5, 120, 240, 360]
cgmValues = [100, 95, 110, 105]
simulatedTime, simulatedCgm = simulate_cgm_data(cgmTimes, cgmValues, amountOfWiggle=3)

# specify the time you want the simulation to start
startTimeHour = 6
startTimeAMPM = "AM"


# %% specify the Predicted CGM Values
cgmTimes = [365, 465, 565, 665, 720]
cgmValues = [105, 90, 78, 90, 100]
predictedTime, predictedCgm = simulate_cgm_data(cgmTimes, cgmValues, amountOfWiggle=2)


# %% speficy the correction range
correction_min = 90
correction_max = 120
suspendThreshold = 60
correction_mean = np.mean([correction_min, correction_max])


# %% set figure properties
versionNumber = 1
figureName = "LoopOverviewV" + str(versionNumber)
outputPath = "."
figureSizeInches = (15, 7)
bgRange = [50, 180]

font = {'family': 'normal',
        'weight': 'bold',
        'size': 15}

plt.rc('font', **font)
coord_color = "#c0c0c0"


# %% make the figure
fig, ax = plt.subplots(figsize=figureSizeInches)
plt.ylim(bgRange)
ax.set_ylabel("BG Level (mg/dL)")
plt.xlim([min(simulatedTime) - 15, max(predictedTime) + 15])

# plot correction range
ax.fill_between([ax.get_xlim()[0], ax.get_xlim()[1]],
                [correction_min, correction_min],
                [correction_max, correction_max],
                facecolor='#B5E7FF', lw=0)

ax.plot([], [], color='#B5E7FF', linewidth=10,
        label="Correction Range: %d-%d" % (correction_min, correction_max))

# plot predicted cgm
ax.plot(predictedTime, predictedCgm, linestyle="--", color="#31B0FF", lw=1, label="Predicted Glucose")

# plot eventual bg
ax.plot(predictedTime[-1], predictedCgm[-1],
        marker='*', markersize=16, color="#31B0FF",
        ls="None", label="Eventual BG = %d" % predictedCgm[-1])

# find and plot minimum BG
min_idx = np.argmin(predictedCgm)
ax.plot(predictedTime[min_idx], predictedCgm[min_idx],
        marker='*', markersize=16, color="red",
        ls="None", label="Minimum BG = %d" % predictedCgm[min_idx])

# plot suspend threshold line
ax.hlines(suspendThreshold, ax.get_xlim()[0], ax.get_xlim()[1],
          colors="red", label="Suspend Threshold = %d" % suspendThreshold)

# plot simulated cgm
ax.scatter(simulatedTime, simulatedCgm, s=10, color="#31B0FF", label="CGM Data")

# plot the delta
ax.vlines(predictedTime[-1], min([correction_mean, predictedCgm[-1]]),
          max([correction_mean, predictedCgm[-1]]), linewidth=5,
          colors="purple", label="Delta")

# define the legend
leg = plt.legend(scatterpoints=3, edgecolor="black")
for text in leg.get_texts():
    text.set_color('#606060')
    text.set_weight('normal')

# set tick marks
minuteTicks = np.arange(0, (len(simulatedTime) + len(predictedTime)) * 5 + 1, 60)
hourTicks = np.int64(minuteTicks / 60)
hourLabels = make_hour_labels(startTimeHour, startTimeAMPM, hourTicks)
ax.set_xticks(minuteTicks)
ax.set_xticklabels(hourLabels)

# set spine and background grid colors
ax.spines['bottom'].set_color(coord_color)
ax.spines['top'].set_color(coord_color)
ax.spines['left'].set_color(coord_color)
ax.spines['right'].set_color(coord_color)
ax.grid(ls='-', color=coord_color)

# turn off the left and right borders
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)

# set the colors of the labels
ax.xaxis.label.set_color(coord_color)
ax.tick_params(axis='x', colors=coord_color)
ax.yaxis.label.set_color(coord_color)
ax.tick_params(axis='y', colors=coord_color)

plt.savefig(os.path.join(outputPath, figureName + ".png"))
plt.show()
plt.close('all')


    # %%

#
## %% figure properties
#fig, ax = plt.subplots(figsize=(12,4))
#
#font = {'family' : 'normal',
#        'weight' : 'bold',
#        'size'   : 15}
#
#plt.rc('font', **font)
#coord_color = "#c0c0c0"
#
#f,a = plt.subplots()
#f.set_size_inches(15, 7)
#plt.ylim([50,180])
#plt.xlim([1,7])
#
#a.spines['bottom'].set_color(coord_color)
#a.spines['top'].set_color(coord_color)
#a.spines['left'].set_color(coord_color)
#a.spines['right'].set_color(coord_color)
#a.xaxis.label.set_color(coord_color)
#a.tick_params(axis='x', colors=coord_color)
#a.yaxis.label.set_color(coord_color)
#a.tick_params(axis='y', colors=coord_color)
#a.spines['right'].set_visible(False)
#a.spines['left'].set_visible(False)
#
## Data
#x_ticks = [2,3,4,5,6,7,8,9]
#labels = ["%d PM" % x1 for x1 in x_ticks]
#plt.xticks(x_ticks, labels)
#
#x_smooth = np.linspace(x.min(), x.max(), int((x.max() - x.min()) * 60 / 5))
#warnings.filterwarnings('ignore')
#y_smooth = spline(x, y, x_smooth)
#warnings.filterwarnings('default')
#
#x_hist, x_predict = np.split(x_smooth, 2)
#y_hist, y_predict = np.split(y_smooth, 2)
#
#noise = np.random.normal(-1,1,len(y_hist))
#noise[-1] = 0
#
#correction_min = 90
#correction_max = 120
#
## correction Range
#a.fill_between([1,9], [correction_min,correction_min], [correction_max,correction_max], facecolor='#B5E7FF', lw=0)
#plt.plot([], [], color='#B5E7FF', linewidth=10, label="correction Range: %d-%d" % (correction_min,correction_max))
#
## background grid
#a.grid(ls='-',color=coord_color)
#
## Plot mock CGM data
#plt.scatter(x_hist,y_hist+noise, color="#31B0FF")
#
## Plot mock forecast
#plt.plot(x_predict,y_predict, linestyle="--", color="#31B0FF", lw=2)
#
## Plot eventual BG
#plt.plot(x_predict[-1],y_predict[-1], marker='>', markersize=10, color="white", ls="None", label="Eventual BG = %d" % y_predict[-1])
#
## Plot minimum BG
#min_idx = np.argmin(y_predict)
#plt.plot(x_predict[min_idx],y_predict[min_idx], marker='v', markersize=10, color="red", ls="None", label="Minimum BG = %d" % y_predict[min_idx])
#
#l = plt.legend(numpoints=1)
#for text in l.get_texts():
#    text.set_color('#606060')
#    text.set_weight('normal')
#
#plt.show()


#Temp Basal Recommendations (Logic)
#There are four cases in which the loop algorithm will implement a temporary basal:
#b(td) > maxCorrectionRange
#b(td) < minCorrectionRangeAND  minb(t)>suspendThreshold
#maxCorrectionRange>b(td) > minCorrectionRangeANDsuspendThreshold<minb(t)<minCorrectionRange
#minb(t)<suspendThreshold
#
#Case 1 b(td) > maxCorrectionRange
#<insert figure>
#If the eventual blood glucose value is greater than the correction range, the loop will set a temporary basal that should bring the blood glucose level within the correction range. Specifically, a difference or delta between the eventual blood glucose level and midpoint or average value of the correction range is calculated and the currently scheduled basal rate is increased as follows:
# bg=b(td) -midCorrectionRange
#tempBasal(to:t30min)=minbasalRate(to)+bgISF; maxBasalRate
#
#Case 2 b(td) < minCorrectionRange AND minb(t)>suspendThreshold
#<insert figure>
#If the eventual blood glucose value is less than the correction range, AND none of the predictions fall below the suspend threshold, then the loop algorithm will set a temporary basal that should bring the blood glucose level within the correction range. Specifically, a difference or delta between the eventual blood glucose level and midpoint or average value of the correction range is calculated and the currently scheduled basal rate is increased as follows:
# bg=b(td) -midCorrectionRange
#tempBasal(to:t30min)=maxbasalRate(to)+bgISF; 0
#
#NOTE: the logic and equations here are very similar to Case 1, but in this casebgwill be negative, so the net effect will be a decrease in the basal rate.
#Case 3 maxCorrectionRange>b(td) > minCorrectionRangeANDsuspendThreshold<minb(t)<minCorrectionRange
#<insert figure>
#If the eventual predicted blood glucose value is within the correction range, AND the minimum predicted blood glucose value is greater than the suspend threshold, but lower than the correction range, then cancel any temporary basals and let the pump default to its scheduled basal rate.
#tempBasal(to:t30min)=basalRate(to)
#Case 4 minb(t)<suspendThreshold
#<insert figure>
#If the minimum predicted blood glucose value goes below the suspend threshold, then suspend the pump, which is equivalent to setting a temp basal of zero:
#tempBasal(to:t30min)=0