"""
description: A convenience class to provide domain specific parsed objects from the loop report parser.

author: Russell Wilson
dependencies: loop_report_parser.py
* <>
license: BSD-2-Clause
"""

from loop_report_parser import parse_loop_report, Sections
import os
import re
import json
import pandas as pd


class LoopReport:
    def parse_by_file(self, path: str, file_name: str) -> dict:
        try:
            if not os.path.isdir(path) or not os.path.isfile(f"{path}/{file_name}"):
                raise RuntimeError("The file path or file name passed in is invalid.")
        except:
            raise RuntimeError("The file path or file name passed in is invalid.")

        return self.__parse(path, file_name)

    def parse_by_directory(self, directory: dict) -> list:
        try:
            if not os.path.isdir(directory):
                raise RuntimeError("The directory passed in is invalid.")
        except:
            raise RuntimeError("The directory passed in is invalid.")

        all_dict_list = []
        for file_name in os.listdir(directory):
            if file_name.endswith(".md"):
                all_dict_list.append(self.__parse(directory, file_name))
        return all_dict_list

    def __parse(self, path, file_name) -> dict:
        loop_report_dict = {}
        dict = parse_loop_report(path, file_name)
        loop_report_dict["file_name"] = file_name
        if Sections.LOOP_VERSION in dict:
            try:
                loop_report_dict["loop_version"] = dict[Sections.LOOP_VERSION][
                    Sections.LOOP_VERSION
                ]
            except:
                print("handled error loop_version")

        if Sections.DEVICE_DATA_MANAGER in dict:
            try:
                self.__device_data_manager = dict[Sections.DEVICE_DATA_MANAGER]
            except:
                print("handled error device data manager")

        if Sections.RILEY_LINK_DEVICE in dict:
            try:
                riley_link_device = dict[Sections.RILEY_LINK_DEVICE]
                loop_report_dict["rileyLink_radio_firmware"] = riley_link_device[
                    "radioFirmware"
                ].strip()
                loop_report_dict["rileyLink_ble_firmware"] = riley_link_device[
                    "bleFirmware"
                ].strip()
            except:
                print("handled error riley link device")

        if Sections.CARB_STORE in dict:
            try:
                carb_store = dict[Sections.CARB_STORE]
                temp = (
                    carb_store["carbRatioSchedule"]
                    .replace("[", "{")
                    .replace("]", "}")
                    .replace("{{", "{")
                    .replace("}}", "}")
                    .replace('"items": {{', '"items": [{')
                    .replace('"items": {', '"items": [{')
                    .replace("}}", "}]")
                    .replace('}, "unit"', '}], "unit"')
                    .replace('}, "timeZone"', '}], "timeZone"')
                )

                if temp[-1:] != "}":
                    temp = temp + "}"

                carb_ratio_schedule = json.loads(temp)

                loop_report_dict["carb_ratio_unit"] = carb_ratio_schedule["unit"]
                loop_report_dict["carb_ratio_timeZone"] = carb_ratio_schedule[
                    "timeZone"
                ]
                loop_report_dict["carb_ratio_schedule"] = carb_ratio_schedule["items"]

                default_absorption_times = json.loads(
                    carb_store["defaultAbsorptionTimes"]
                    .replace("(", "{")
                    .replace(")", "}")
                    .replace("fast", '"fast"')
                    .replace("medium", '"medium"')
                    .replace("slow", '"slow"')
                )
                loop_report_dict[
                    "carb_default_absorption_times_fast"
                ] = default_absorption_times["fast"]
                loop_report_dict[
                    "carb_default_absorption_times_medium"
                ] = default_absorption_times["medium"]
                loop_report_dict[
                    "carb_default_absorption_times_slow"
                ] = default_absorption_times["slow"]

                temp = (
                    carb_store["insulinSensitivitySchedule"]
                    .replace("[", "{")
                    .replace("]", "}")
                    .replace("{{", "{")
                    .replace("}}", "}")
                    .replace('"items": {{', '"items": [{')
                    .replace('"items": {', '"items": [{')
                    .replace("}}", "}]")
                    .replace('}, "unit"', '}], "unit"')
                    .replace('}, "timeZone"', '}], "timeZone"')
                )

                if temp[-1:] != "}":
                    temp = temp + "}"

                insulin_sensitivity_factor_schedule = json.loads(temp)
                loop_report_dict[
                    "insulin_sensitivity_factor_schedule"
                ] = insulin_sensitivity_factor_schedule["items"]
                loop_report_dict[
                    "insulin_sensitivity_factor_timeZone"
                ] = insulin_sensitivity_factor_schedule["timeZone"]
                loop_report_dict[
                    "insulin_sensitivity_factor_unit"
                ] = insulin_sensitivity_factor_schedule["unit"]

            except:
                print("handled error carb store")

        if Sections.DOSE_STORE in dict:
            try:
                dose_store = dict[Sections.DOSE_STORE]
                basal_profile = json.loads(
                    dose_store["basalProfile"]
                    .replace("[", "{")
                    .replace("]", "}")
                    .replace("{{", "{")
                    .replace("}}", "}")
                    .replace(": {", ": [{")
                    .replace("}}", "}]}")
                    .replace('}, "timeZone"', '}], "timeZone"')
                )
                loop_report_dict["basal_rate_timeZone"] = basal_profile["timeZone"]
                loop_report_dict["basal_rate_schedule"] = basal_profile["items"]

                loop_report_dict["insulin_model"] = re.search(
                    r"Optional\((.+?)\(Exponential", dose_store["insulinModel"]
                ).group(1)
                loop_report_dict["insulin_action_duration"] = float(
                    re.search(
                        "actionDuration: (.+?), peakActivityTime",
                        dose_store["insulinModel"],
                    ).group(1)
                )

            except:
                print("handled error dose store")

        minimed_pump_manager = None
        omnipod_pump_manager = None
        if (
            Sections.MINIMED_PUMP_MANAGER in dict
            or Sections.OMNIPOD_PUMP_MANAGER in dict
        ):
            if Sections.MINIMED_PUMP_MANAGER in dict:
                try:
                    minimed_pump_manager = dict[Sections.MINIMED_PUMP_MANAGER]
                except:
                    print("handled error minimed pump manager")
            if Sections.OMNIPOD_PUMP_MANAGER in dict:
                try:
                    omnipod_pump_manager = dict[Sections.OMNIPOD_PUMP_MANAGER]
                except:
                    print("handled error omnipod pump manager")

            self.__set_pump_manager_type(
                loop_report_dict, minimed_pump_manager, omnipod_pump_manager
            )

        if Sections.WATCH_DATA_MANAGER in dict:
            try:
                watch_data_manager = dict[Sections.WATCH_DATA_MANAGER]
                loop_report_dict["is_watch_app_installed"] = watch_data_manager[
                    "isWatchAppInstalled"
                ].strip()

            except:
                print("handled error watch data manager")

        if Sections.LOOP_DATA_MANAGER in dict:
            try:
                loop_data_manager = dict[Sections.LOOP_DATA_MANAGER]

                loop_report_dict["maximum_basal_rate"] = float(
                    re.search(
                        r"maximumBasalRatePerHour: Optional\((.+?)\), maximumBolus",
                        loop_data_manager["settings"],
                    ).group(1)
                )

                loop_report_dict["maximum_bolus"] = float(
                    re.search(
                        r"maximumBolus: Optional\((.+?)\), suspendThreshold",
                        loop_data_manager["settings"],
                    ).group(1)
                )

                temp = re.search(
                    "retrospectiveCorrectionEnabled: (.+?), retrospectiveCorrection",
                    loop_data_manager["settings"],
                )
                if temp:
                    loop_report_dict["retrospective_correction_enabled"] = temp.group(1)

                loop_report_dict["suspend_threshold"] = float(
                    re.search(
                        r"Loop.GlucoseThreshold\(value: (.+?), unit",
                        loop_data_manager["settings"],
                    ).group(1)
                )

                start_index = loop_data_manager["settings"].index("suspendThreshold")
                end_index = loop_data_manager["settings"].index(
                    "retrospectiveCorrectionEnabled"
                )
                substr = loop_data_manager["settings"][start_index:end_index]

                unit = substr.index("unit")
                start_index = unit + 6
                check = ""
                while check != ")":
                    unit += 1
                    check = substr[unit]
                loop_report_dict["suspend_threshold_unit"] = substr[start_index:unit]

                start_index = loop_data_manager["settings"].index("overrideRanges")
                end_index = loop_data_manager["settings"].index(
                    "maximumBasalRatePerHour"
                )
                substr = loop_data_manager["settings"][start_index:end_index]

                workout = substr.index("workout")
                start_index = workout + 10
                check = ""
                while check != "]":
                    workout += 1
                    check = substr[workout]
                loop_report_dict["override_range_workout"] = eval(
                    substr[start_index : workout + 1]
                )
                try:
                    premeal = substr.index("preMeal")
                    start_index = premeal + 10
                    check = ""

                    while check != "]":
                        premeal += 1
                        check = substr[premeal]
                    loop_report_dict["override_range_premeal"] = eval(
                        substr[start_index : premeal + 1]
                    )
                except:
                    print("preMeal is not in loop data")

            except:
                print("handled error loop data manager")

        if Sections.INSULIN_COUNTERACTION_EFFECTS in dict:
            try:
                ice_list = dict[Sections.INSULIN_COUNTERACTION_EFFECTS]
                df = pd.DataFrame(columns=["start_time", "end_time", "value", 'units'])
                ice_list.pop(0)
                ice_list.pop(len(ice_list) - 1)

                for items in ice_list:
                    start, end, value = items.split(",")
                    df = df.append(
                        {"start_time": start, "end_time": end, "value": value, "units": "mg/dL/min"},
                        ignore_index=True,
                    )

                loop_report_dict["insulin_counteration_effects"] = df

            except:
                print("handled error INSULIN_COUNTERACTION_EFFECTS")

        if Sections.RETROSPECTIVE_GLUCOSE_DISCREPANCIES_SUMMED in dict:
            try:
                local_list = dict[Sections.RETROSPECTIVE_GLUCOSE_DISCREPANCIES_SUMMED]
                df = pd.DataFrame(columns=["start_time", "end_time", "value", "units"])
                local_list.pop(0)
                local_list.pop(len(local_list) - 1)

                for items in local_list:
                    start, end, value = items.split(",")
                    df = df.append(
                        {"start_time": start, "end_time": end, "value": value, "units": "mg/dL"},
                        ignore_index=True,
                    )

                loop_report_dict["retrospective_glucose_discrepancies_summed"] = df

            except:
                print("handled error RETROSPECTIVE_GLUCOSE_DISCREPANCIES")

        if Sections.INSULIN_COUNTERACTION_EFFECTS in dict:
            try:
                local_list = dict[Sections.INSULIN_COUNTERACTION_EFFECTS]
                df = pd.DataFrame(columns=["start_time", "end_time", "value", "units"])
                local_list.pop(0)
                local_list.pop(len(local_list) - 1)

                for items in local_list:
                    start, end, value = items.split(",")
                    df = df.append(
                        {"start_time": start, "end_time": end, "value": value, "units": "mg/dL/min"},
                        ignore_index=True,
                    )

                loop_report_dict["insulin_counteraction_effects"] = df

            except:
                print("handled error INSULIN_COUNTERACTION_EFFECTS")

        if Sections.GET_RESERVOIR_VALUES in dict:
            try:
                local_list = dict[Sections.GET_RESERVOIR_VALUES]
                df = pd.DataFrame(columns=["start_time", "value", "units"])
                local_list.pop(0)
                local_list.pop(len(local_list) - 1)

                for items in local_list:
                    start, value = items.split(",")
                    df = df.append(
                        {"start_time": start, "value": value, "units": "unitVolume"}, ignore_index=True
                    )

                loop_report_dict["get_reservoir_values"] = df

            except:
                print("handled error GET_RESERVOIR_VALUES")

        if Sections.PREDICTED_GLUCOSE in dict:
            try:
                local_list = dict[Sections.PREDICTED_GLUCOSE]
                df = pd.DataFrame(columns=["start_time", "value", "units"])
                local_list.pop(0)
                local_list.pop(len(local_list) - 1)

                for items in local_list:
                    start, value = items.split(",")
                    df = df.append(
                        {"start_time": start, "value": value, "units": "mg/dL"}, ignore_index=True
                    )

                loop_report_dict["predicted_glucose"] = df

            except:
                print("handled error PREDICTED_GLUCOSE")

        if Sections.RETROSPECTIVE_GLUCOSE_DISCREPANCIES in dict:
            try:
                local_list = dict[Sections.RETROSPECTIVE_GLUCOSE_DISCREPANCIES]
                df = pd.DataFrame(columns=["start_time", "value", "units"])
                local_list.pop(0)
                local_list.pop(len(local_list) - 1)

                for items in local_list:
                    start, value = items.split(",")
                    df = df.append(
                        {"start_time": start, "value": value, "units": "mg/dL"}, ignore_index=True
                    )

                loop_report_dict["retrospective_glucose_discrepancies"] = df

            except:
                print("handled error RETROSPECTIVE_GLUCOSE_DISCREPANCIES")

        if Sections.CARB_EFFECT in dict:
            try:
                local_list = dict[Sections.CARB_EFFECT]
                df = pd.DataFrame(columns=["start_time", "value", "units"])
                local_list.pop(0)
                local_list.pop(len(local_list) - 1)

                for items in local_list:
                    start, value = items.split(",")
                    df = df.append(
                        {"start_time": start, "value": value, "units": "mg/dL"}, ignore_index=True
                    )

                loop_report_dict["carb_effect"] = df

            except:
                print("handled error CARB_EFFECT")

        if Sections.INSULIN_EFFECT in dict:
            try:
                local_list = dict[Sections.INSULIN_EFFECT]
                df = pd.DataFrame(columns=["start_time", "value", "units"])
                local_list.pop(0)
                local_list.pop(len(local_list) - 1)

                for item in local_list:
                    start, value = item.split(",")
                    df = df.append(
                        {"start_time": start, "value": value, "units": "mg/dL"}, ignore_index=True
                    )

                loop_report_dict["insulin_effect"] = df

            except:
                print("handled error INSULIN_EFFECT")

        if Sections.GET_NORMALIZED_PUMP_EVENT_DOSE in dict:
            try:
                local_list = dict[Sections.GET_NORMALIZED_PUMP_EVENT_DOSE]
                complete_df = pd.DataFrame()
                for item in local_list:
                    record_dict = {}
                    item = item.replace("DoseEntry(", "")
                    item = item.replace(item[len(item) - 1], "")
                    key_value = item.split(", ")

                    for v in key_value:
                        aux = v.split(": ")
                        record_dict[aux[0]] = aux[1]
                    # if complete_df:
                    df = pd.DataFrame([record_dict], columns=record_dict.keys())
                    complete_df = pd.concat([complete_df, df], axis=0)

                loop_report_dict["get_normalized_pump_even_dose"] = complete_df
            except:
                print("handled error GET_NORMALIZED_PUMP_EVENT_DOSE")

        if Sections.GET_NORMALIZED_DOSE_ENTRIES in dict:
            try:
                local_list = dict[Sections.GET_NORMALIZED_DOSE_ENTRIES]
                complete_df = pd.DataFrame()
                for item in local_list:
                    record_dict = {}
                    item = item.replace("DoseEntry(", "")
                    item = item.replace(item[len(item) - 1], "")
                    key_value = item.split(", ")

                    for v in key_value:
                        aux = v.split(": ")
                        record_dict[aux[0]] = aux[1]
                    # if complete_df:
                    df = pd.DataFrame([record_dict], columns=record_dict.keys())
                    complete_df = pd.concat([complete_df, df], axis=0)

                loop_report_dict["get_normalized_dose_entries"] = complete_df
            except:
                print("handled error GET_NORMALIZED_DOSE_ENTRIES")

        if Sections.CACHED_DOSE_ENTRIES in dict:
            try:
                local_list = dict[Sections.CACHED_DOSE_ENTRIES]
                complete_df = pd.DataFrame()
                for item in local_list:
                    record_dict = {}
                    item = item.replace("DoseEntry(", "")
                    item = item.replace(item[len(item) - 1], "")
                    key_value = item.split(", ")

                    for v in key_value:
                        aux = v.split(": ")
                        record_dict[aux[0]] = aux[1]
                    # if complete_df:
                    df = pd.DataFrame([record_dict], columns=record_dict.keys())
                    complete_df = pd.concat([complete_df, df], axis=0)

                loop_report_dict["cached_dose_entries"] = complete_df
            except:
                print("handled error CACHED_DOSE_ENTRIES")

        if Sections.GET_PUMP_EVENT_VALUES in dict:
            try:
                local_list = dict[Sections.GET_PUMP_EVENT_VALUES]
                complete_df = pd.DataFrame()
                for item in local_list:
                    record_dict = {}
                    item = item.replace("PersistedPumpEvent(", "")
                    item = item.replace(item[len(item) - 1], "")
                    key_value = item.split(", ")

                    for v in key_value:
                        aux = v.split(": ")
                        record_dict[aux[0]] = aux[1]
                    # if complete_df:
                    df = pd.DataFrame([record_dict], columns=record_dict.keys())
                    complete_df = pd.concat([complete_df, df], axis=0, sort=False)

                loop_report_dict["get_pump_event_values"] = complete_df
            except:
                print("handled error GET_PUMP_EVENT_VALUES")

        if Sections.MESSAGE_LOG in dict:
            local_list = dict[Sections.MESSAGE_LOG]
            loop_report_dict["message_log"] = local_list

        if Sections.G5_CGM_MANAGER in dict:
            try:
                temp_dict = dict[Sections.G5_CGM_MANAGER]
                cgmblekit = temp_dict['latestReading']
                cgmblekit= cgmblekit.replace("Optional(CGMBLEKit.Glucose(glucoseMessage: CGMBLEKit.GlucoseSubMessage(", "")
                cgmblekit = cgmblekit.replace("))", "")

                split_list = cgmblekit.split(",")

                dictionary_complete = {}

                if 'transmitter' in temp_dict:
                    dictionary_complete['transmitter'] = temp_dict['transmitter']

                if 'providesBLEHeartbeat' in temp_dict:
                    dictionary_complete['providesBLEHeartbeat'] = temp_dict['providesBLEHeartbeat']
                dictionary = {}
                timeMessage = {}
                glucoseMessage = {}
                latestReading = {}
                for item in split_list:
                    if "timeMessage:" in item:
                        item = item.replace("timeMessage: CGMBLEKit.TransmitterTimeRxMessage(", "")
                        keyvalue = item.split(":")
                        timeMessage['status'] = keyvalue[1].strip('"\'')

                    else:
                        item = item.replace(")", "")
                        keyvalue = item.split(":")
                        m = keyvalue[0].strip('\'')
                        m = m.replace("\"", "").strip()
                        dictionary[m] = keyvalue[1].strip('"\'')


                glucoseMessage['timestamp'] = dictionary['timestamp']
                glucoseMessage['glucoseIsDisplayOnly'] = dictionary['glucoseIsDisplayOnly']
                glucoseMessage['glucose'] = dictionary['glucose']
                glucoseMessage['trend'] = dictionary['trend']


                timeMessage['currentTime'] = dictionary['currentTime']
                timeMessage['sessionStartTime'] = dictionary['sessionStartTime']

                latestReading['glucoseMessage'] = glucoseMessage
                latestReading['timeMessage'] = timeMessage
                latestReading['transmitterID'] = dictionary['transmitterID']
                latestReading['status'] = dictionary['status']
                latestReading['sessionStartDate'] = dictionary['sessionStartDate']
                latestReading['lastCalibration'] = dictionary['lastCalibration']
                latestReading['readDate'] = dictionary['readDate']

                dictionary_complete['latestReading'] = latestReading

                loop_report_dict["g5_cgm_manager"] = dictionary_complete
            except:
                print("handled error G5_CGM_MANAGER")

        if Sections.DEX_CGM_MANAGER in dict:
            try:
                loop_report_dict["dex_cgm_manager"] = dict[Sections.DEX_CGM_MANAGER]
            except:
                print("handled error DEX_CGM_MANAGER")

        if Sections.STATUS_EXTENSION_DATA_MANAGER in dict:
            try:
                status_extension_data_manager = dict[Sections.STATUS_EXTENSION_DATA_MANAGER]
                temp = status_extension_data_manager['statusExtensionContext']
                temp = temp.replace("Optional([", "")
                values_index = temp.index("values")
                unit_index = temp.index("unit")
                values = temp[values_index: unit_index]
                values = values.replace(": [", "")
                values = values.replace("values", "")
                values = values.replace("]", "")
                values = values.replace(', "', '')
                values_list = values.split(",")

                newstr = temp[:values_index] + temp[unit_index:]
                newstr = newstr.replace('"', '')
                newstr = newstr.strip()
                temp_list = newstr.split(",")

                statusExtensionContext = {}

                dictionary = {}
                for item in temp_list:
                    if 'sensor' in item:
                        item = "isStateValid: " + item.replace(' sensor: [isStateValid: ', '')
                        self.add_to_dictionary(dictionary, item)

                    elif 'lastLoopCompleted' in item:
                        dictionary["lastLoopCompleted"] = item.replace('lastLoopCompleted: ', '')

                    elif 'predictedGlucose' in item:
                        dictionary["startDate"] = item.replace(' predictedGlucose: [startDate: ', '')

                    elif 'start:' in item:
                        dictionary["start"] = item.replace('start: ', '')

                    elif 'end:' in item:
                        dictionary["end"] = item.replace('end: ', '').replace("]", "")

                    elif 'percentage' in item:
                        item = "percentage: " + item.replace(' netBasal: [percentage: ', '')
                        self.add_to_dictionary(dictionary, item)

                    elif 'reservoirCapacity' in item:
                        item = item.replace("])", "")
                        self.add_to_dictionary(dictionary, item)
                    else:
                        self.add_to_dictionary(dictionary, item)

                sensor = {}
                sensor["isStateValid"] = dictionary["isStateValid"]
                sensor["stateDescription"] = dictionary["stateDescription"]
                sensor["trendType"] = dictionary["trendType"]
                sensor["isLocal"] = dictionary["isLocal"]

                predictedGlucose = {}
                predictedGlucose["startDate"] = dictionary["startDate"]
                predictedGlucose["values"] = values_list
                predictedGlucose["unit"] = dictionary["unit"]
                predictedGlucose["interval"] = dictionary["interval"]

                netBasal = {}
                netBasal["percentage"] = dictionary["percentage"]
                netBasal["start"] = dictionary["start"]
                netBasal["rate"] = dictionary["rate"]
                netBasal["end"] = dictionary["end"]

                statusExtensionContext['lastLoopCompleted'] = dictionary['lastLoopCompleted']
                statusExtensionContext['sensor'] = sensor
                statusExtensionContext['predictedGlucose'] = predictedGlucose
                statusExtensionContext['netBasal'] = netBasal
                statusExtensionContext['batteryPercentage'] = dictionary['batteryPercentage']
                statusExtensionContext['version'] = dictionary['version']
                statusExtensionContext['reservoirCapacity'] = dictionary['reservoirCapacity']

                status_extension_data_manager['statusExtensionContext'] = statusExtensionContext

                loop_report_dict["status_extension_data_manager"] = status_extension_data_manager
            except:
                print("handled error STATUS_EXTENSION_DATA_MANAGER")

        if Sections.RILEY_LINK_PUMP_MANAGER in dict:
            try:
                loop_report_dict["riley_link_pump_manager"] = dict[
                    Sections.RILEY_LINK_PUMP_MANAGER
                ]
            except:
                print("handled error RILEY_LINK_PUMP_MANAGER")

        if Sections.RILEY_LINK_DEVICE_MANAGER in dict:
            try:
                loop_report_dict["riley_link_device_manager"] = dict[
                    Sections.RILEY_LINK_DEVICE_MANAGER
                ]
            except:
                print("handled error RILEY_LINK_DEVICE_MANAGER")

        if Sections.PERSISTENCE_CONTROLLER in dict:
            try:
                loop_report_dict["persistence_controller"] = dict[
                    Sections.PERSISTENCE_CONTROLLER
                ]
            except:
                print("handled error PERSISTENCE_CONTROLLER")

        if Sections.INSULIN_DELIVERY_STORE in dict:
            try:
                loop_report_dict["insulin_delivery_store"] = dict[
                    Sections.INSULIN_DELIVERY_STORE
                ]
            except:
                print("handled error INSULIN_DELIVERY_STORE")

        if Sections.CACHED_CARB_ENTRIES in dict:
            try:
                complete_df = pd.DataFrame()
                items = dict[Sections.CACHED_CARB_ENTRIES]
                items.pop(0)
                items.pop(len(items) - 1)
                columns = [
                    "sampleUUID",
                    "syncIdentifier",
                    "syncVersion",
                    "startDate",
                    "quantity",
                    "foodType",
                    "absorptionTime",
                    "createdByCurrentApp",
                    "externalID",
                    "isUploaded",
                ]
                for item in items:
                    empty, sampleUUID, syncIdentifier, syncVersion, startDate, quantity, foodType, absorptionTime, createdByCurrentApp, externalID, isUploaded = item.split(
                        ","
                    )
                    record_dict = {
                        "sampleUUID": sampleUUID,
                        "syncIdentifier": syncIdentifier,
                        "syncVersion": syncVersion,
                        "startDate": startDate,
                        "quantity": quantity,
                        "foodType": foodType,
                        "absorptionTime": absorptionTime,
                        "createdByCurrentApp": createdByCurrentApp,
                        "externalID": externalID,
                        "isUploaded": isUploaded,
                    }
                    df = pd.DataFrame([record_dict], columns=columns)
                    complete_df = pd.concat([complete_df, df], axis=0)
                loop_report_dict["cached_carb_entries"] = complete_df
            except:
                print("handled error CACHED_CARB_ENTRIES")

        # todo: still need to parse out section further
        if Sections.GLUCOSE_STORE in dict:
            try:
                loop_report_dict["glucose_store"] = dict[Sections.GLUCOSE_STORE]

            except:
                print("handled error GLUCOSE_STORE")

        if Sections.CACHED_GLUCOSE_SAMPLES in dict:
            try:
                local_list = dict[Sections.CACHED_GLUCOSE_SAMPLES]
                complete_df = pd.DataFrame()
                for item in local_list:
                    record_dict = {}
                    item = item.replace("StoredGlucoseSample(", "")
                    item = item.replace(item[len(item) - 1], "")
                    key_value = item.split(", ")

                    for v in key_value:
                        aux = v.split(": ")
                        record_dict[aux[0]] = aux[1]
                    # if complete_df:
                    df = pd.DataFrame([record_dict], columns=record_dict.keys())
                    complete_df = pd.concat([complete_df, df], axis=0, ignore_index=True)

                loop_report_dict["cached_glucose_samples"] = complete_df
            except:
                print("handled error CACHED_GLUCOSE_SAMPLES")

        return loop_report_dict

    def add_to_dictionary(self, dictionary, item):
        keyvalue = item.split(":")
        m = keyvalue[0].strip('\'')
        m = m.replace("]", "").strip()
        dictionary[m] = keyvalue[1].strip('"\'').replace("]", "")

    def __set_pump_manager_type(
        self, loop_report_dict, minimed_pump_manager, omnipod_pump_manager
    ):
        if minimed_pump_manager:
            loop_report_dict["pump_manager_type"] = "minimed"
            try:
                loop_report_dict["pump_model"] = minimed_pump_manager[
                    "pumpModel"
                ].strip()
            except:
                print("pump model in minimed_pump_manager is not available")

        elif omnipod_pump_manager:
            loop_report_dict["pump_manager_type"] = "omnipod"
            try:
                loop_report_dict["pm_version"] = omnipod_pump_manager[
                    "pmVersion"
                ].strip()
                loop_report_dict["pi_version"] = omnipod_pump_manager[
                    "piVersion"
                ].strip()
            except:
                print(
                    "pm version or pi version in omnipod_pump_manager is not available"
                )

        else:
            loop_report_dict["pump_manager_type"] = "unknown"
