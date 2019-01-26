#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 25 06:55:48 2019

@author: ed
"""

from loop_report_parser import parse_loop_report, Sections
import os
import pandas as pd
import pdb

dateString = "2019-01-16 08-39-03-06-00"

allDataDict = parse_loop_report("/Users/ed/Desktop/Loop Report 2019-01-16 08-39-03-06-00.md")

loop_dict = allDataDict[Sections.LOOP_VERSION]
asdf = pd.DataFrame(allDataDict[Sections.DEVICE_DATA_MANAGER])

df = pd.DataFrame()
# [X] Loop version
loopVersion = allDataDict['loop_version']['loop_version']
df.loc["loopVersion", dateString] = loopVersion

# [X] “pumpModel”
pumpManager = [s for s in list(allDataDict) if (("pump_manager" in s) & ("riley_link" not in s))]
if len(pumpManager) > 1:
    # we only expect one pump manager (not including the riley_link_pump_manager), if this is not
    # the case then flag this case.
    pdb.set_trace()
else:
    pumpModel = (allDataDict[pumpManager[0]]['pumpModel']).replace("\n", "").replace(" ", "")
    df.loc["pumpModel", dateString] = pumpModel

# [X] “firmwareVersion” of RileyLinkDevice
rileyLinkRadioFirmware = allDataDict['riley_link_device']['radioFirmware'].replace(")\n", "").replace(" Optional(", "")
df.loc["rileyLinkRadioFirmware", dateString] = rileyLinkRadioFirmware

rileyLinkBleFirmware = allDataDict['riley_link_device']['bleFirmware'].replace(")\n", "").replace(" Optional(", "")
df.loc["rileyLinkBleFirmware", dateString] = rileyLinkBleFirmware


# %% here are the items for the MVP version
### CarbStore
#“carbRatioSchedule” info
#“defaultAbsorptionTimes” info
#“insulinSensitivitySchedule” values
# ## DoseStore
#“insulinModel” info
#“BasalProfile” info
#PumpManager type (OmnipodPumpManager vs MinimedPumpManager)
#Whether the user is using the Loop Apple Watch App (WatchDataManager -> isWatchAppInstalled)
#LoopDataManager:
#    * maxBasalRate
#    * maxBolus
#    * retrospectiveCorrectionEnabled
#    * suspendThreshold
#    * overrideRanges