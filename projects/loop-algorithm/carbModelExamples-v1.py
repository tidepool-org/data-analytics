#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 11 16:48:06 2018

@author: ed
"""

import numpy as np
import pandas as pd
import datetime as dt
import sys
import matplotlib.pyplot as plt


# %% simple example

# TODO: make this a generic function as it is called by carbEffect and insulinEffect

deliveryTime=dt.datetime.now()
timeStepSize=5
effectLength=8
startTime = pd.to_datetime(deliveryTime).round(str(timeStepSize) + "min")
endTime = startTime + pd.Timedelta(8, unit="h")
rng = pd.date_range(startTime, endTime, freq=(str(timeStepSize) + "min"))
carbEffect = pd.DataFrame(rng, columns=["dateTime"])
carbEffect["minutesSinceDelivery"] = np.arange(0, (effectLength * 60) + 1, timeStepSize)

# carb specific parameters
carbModel = "linear"  # other optoin is parabolic
absorptionTime = 4  # defaults are 2, 3, or 4 hours
totalCarbs = 1  # in grams (g)
carbRatio = 1  # in grams per unit (g/U)
isf = 1  # insulin sensitivity factor in (mg/dL) / U

# carb effect model
absorptionTimeMinutes = absorptionTime * 60
carbEffect["minutesSinceDelivery"] <= (absorptionTimeMinutes / 2)

# initiate the carb absorption percentage, which also sets all values after the absorptionTime to 1
carbEffect["carbAbsorbPercent"] = np.ones(len(carbEffect))

# THIS IS THE PARABOLIC MODEL THAT IS NO LONGER USED (OR IS ONLY USED IF DYNAMIC MODELING IS OFF,
# WHICH IS NO LONGER AN OPTION.)
if "parabolic" in carbModel:

    # first half of the absorption curve
    firstHalf = carbEffect["minutesSinceDelivery"] <= (absorptionTimeMinutes / 2)
    carbEffect.loc[firstHalf, "carbAbsorbPercent"] = \
        2 / pow(absorptionTimeMinutes, 2) * pow(carbEffect["minutesSinceDelivery"], 2)

    # second half of the absorption curve
    secondHalf = (carbEffect["minutesSinceDelivery"] < absorptionTimeMinutes) & (~firstHalf)
    carbEffect.loc[secondHalf, "carbAbsorbPercent"] = \
        (-1 + 4 / absorptionTimeMinutes * (carbEffect["minutesSinceDelivery"] -
         pow(carbEffect["minutesSinceDelivery"], 2) / (2 * absorptionTimeMinutes)))

else:  # the linear model
    carbEffect.loc[carbEffect["minutesSinceDelivery"] < absorptionTimeMinutes, "carbAbsorbPercent"] = \
        carbEffect["minutesSinceDelivery"] / absorptionTimeMinutes

# set the first point to 0
carbEffect.loc[0, "carbAbsorbPercent"] = 0

# calculate absorbed carbs and unabsorbed carbs
carbEffect["absorbedCarbs"] = totalCarbs * carbEffect["carbAbsorbPercent"]
carbEffect["carbsOnBoard"] = totalCarbs * (1 - carbEffect["carbAbsorbPercent"])
carbEffect["cumulativeGlucoseEffect"] = isf / carbRatio * carbEffect["absorbedCarbs"]
carbEffect["deltaGlucoseEffect"] = \
    carbEffect["cumulativeGlucoseEffect"] - carbEffect["cumulativeGlucoseEffect"].shift()
carbEffect["deltaGlucoseEffect"].fillna(0, inplace=True)


# %% test carb effect models

xData = carbEffect["minutesSinceDelivery"]/60
xLabel = "Time Since Delivery (Hours)"

# carbs absorbed percentage
fig, ax = plt.subplots()
ax.set_xlabel(xLabel)
ax.set_ylabel("Carbs Absorbed (%)")
ax.set_title("Absorption Time = " + str(absorptionTime) + " Hours")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
plt.scatter(xData, carbEffect["carbAbsorbPercent"])

# carbs absorbed
fig, ax = plt.subplots()
ax.set_xlabel(xLabel)
ax.set_ylabel("Carbs Absorbed (g)")
ax.set_title("Total Carbs = " + str(totalCarbs)  + "g, Absorption Time = " + str(absorptionTime) + " Hours")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
plt.scatter(xData, carbEffect["absorbedCarbs"])

# carbs on board
fig, ax = plt.subplots()
ax.set_xlabel(xLabel)
ax.set_ylabel("Carbs-On-Board (g)")
ax.set_title("Total Carbs = " + str(totalCarbs)  + "g, Absorption Time = " + str(absorptionTime) + " Hours")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
plt.scatter(xData, carbEffect["carbsOnBoard"])

# cumulative glucose effect
fig, ax = plt.subplots()
ax.set_xlabel(xLabel)
ax.set_ylabel("Cumulative Glucose Effect (mg/dL)")
ax.set_title("Total Carbs = " + str(totalCarbs)  + "g, ISF = " + str(isf) + " (mg/dL)/U"
             "\nAbsorption Time = " + str(absorptionTime) + " Hours")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
plt.scatter(xData, carbEffect["cumulativeGlucoseEffect"])

# delta BG
fig, ax = plt.subplots()
ax.set_xlabel(xLabel)
ax.set_ylabel(r"$\Delta BG \/ (mg/dL)$")
ax.set_title("Total Carbs = " + str(totalCarbs)  + "g, ISF = " + str(isf) + " (mg/dL)/U"
             "\nAbsorption Time = " + str(absorptionTime) + " Hours")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
plt.scatter(xData, carbEffect["deltaGlucoseEffect"])

