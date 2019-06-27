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
import logging

logger = logging.getLogger("LoopReport")


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
            try:
                if file_name.endswith(".md"):
                    all_dict_list.append(self.__parse(directory, file_name))
            except Exception as e:
                logger.debug("loop parser parse by directory error for file")
                logger.debug(e)
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
                logger.debug("handled error loop_version")

        if Sections.DEVICE_DATA_MANAGER in dict:
            try:
                self.__device_data_manager = dict[Sections.DEVICE_DATA_MANAGER]
            except:
                logger.debug("handled error device data manager")

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
                logger.debug("handled error riley link device")

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
                logger.debug("handled error carb store")

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
                logger.debug("handled error dose store")

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
                    logger.debug("handled error minimed pump manager")
            if Sections.OMNIPOD_PUMP_MANAGER in dict:
                try:
                    omnipod_pump_manager = dict[Sections.OMNIPOD_PUMP_MANAGER]
                except:
                    logger.debug("handled error omnipod pump manager")

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
                logger.debug("handled error watch data manager")

        if Sections.LOOP_DATA_MANAGER in dict:
            try:
                loop_data_manager = dict[Sections.LOOP_DATA_MANAGER]

                try:
                    carbs_on_board = loop_data_manager['carbsOnBoard']
                    carbs_on_board = carbs_on_board.replace('Optional(LoopKit.CarbValue(', '').replace('))', '').replace(')', '')
                    carbs_on_board_list = carbs_on_board.split(",")
                    carbs_on_board_dict = {}
                    for v in carbs_on_board_list:
                        aux = v.split(": ")
                        if 'quantity' in aux[0]:
                            aux[1] = aux[1].replace('g', '')
                            carbs_on_board_dict[aux[0]] = float(aux[1])
                            carbs_on_board_dict["units"] = 'g'
                        else:
                            carbs_on_board_dict[aux[0]] = aux[1]
                    loop_report_dict["carbs_on_board"] = carbs_on_board_dict
                except Exception as e:
                    logger.debug("handled error loop data manager - carbs_on_board")
                    logger.debug(e)

                try:
                    last_temp_basal = loop_data_manager['lastTempBasal']
                    if last_temp_basal != 'nil':
                        last_temp_basal = last_temp_basal.replace('Optional(LoopKit.DoseEntry(','').replace('))', '').replace(')', '')
                        last_temp_basal_list = last_temp_basal.split(",")
                        last_temp_basal_dict = {}
                        for v in last_temp_basal_list:
                            aux = v.split(": ")
                            if 'value' in aux[0]:
                                last_temp_basal_dict[aux[0]] = float(aux[1])
                            else:
                                last_temp_basal_dict[aux[0]] = aux[1]
                        loop_report_dict["last_temp_basal"] = last_temp_basal_dict
                except Exception as e:
                    logger.debug("handled error loop data manager - last_temp_basal")
                    logger.debug(e)

                try:
                    recommended_bolus = loop_data_manager['recommendedBolus']
                    recommended_bolus = recommended_bolus.replace('Optional((recommendation: Loop.BolusRecommendation(', '').replace('))', '').replace(')', '')
                    recommended_bolus_list = recommended_bolus.split(",")
                    recommended_bolus_dict = {}
                    for v in recommended_bolus_list:
                        aux = v.split(": ")
                        if 'amount' in aux[0]:
                            recommended_bolus_dict[aux[0]] = float(aux[1])
                        elif 'pendingInsulin' in aux[0]:
                            recommended_bolus_dict[aux[0]] = float(aux[1])
                        else:
                            recommended_bolus_dict[aux[0]] = aux[1]
                    loop_report_dict["recommended_bolus"] = recommended_bolus_dict
                except Exception as e:
                    logger.debug("handled error loop data manager - recommended_bolus")
                    logger.debug(e)

                try:
                    recommended_temp_basal = loop_data_manager['recommendedTempBasal']
                    if recommended_temp_basal.strip() != 'nil':
                        recommended_temp_basal = recommended_temp_basal.replace('Optional((recommendation: Loop.TempBasalRecommendation(', '').replace('))', '').replace(')', '')
                        recommended_temp_basal_list = recommended_temp_basal.split(",")
                        recommended_temp_basal_dict = {}
                        for v in recommended_temp_basal_list:
                            aux = v.split(": ")
                            if 'unitsPerHour' in aux[0]:
                                recommended_temp_basal_dict[aux[0]] = float(aux[1])
                            elif 'duration' in aux[0]:
                                recommended_temp_basal_dict[aux[0]] = float(aux[1])
                            else:
                                recommended_temp_basal_dict[aux[0]] = aux[1]
                        loop_report_dict["recommended_temp_basal"] = recommended_temp_basal_dict
                except Exception as e:
                    logger.debug("handled error loop data manager - recommended_temp_basal")
                    logger.debug(e)

                try:
                    retrospective_glucose_effect = loop_data_manager['retrospectiveGlucoseEffect']
                    retrospective_glucose_effect = retrospective_glucose_effect.replace("[", "").replace("]", "").replace(
                        "LoopKit.GlucoseEffect(", "")
                    values = retrospective_glucose_effect.split(")")
                    values.pop(len(values) - 1)
                    retrospective_glucose_effect_list = []
                    for value in values:
                        items = value.split(",")
                        dictionary = {}

                        for item in items:
                            if 'startDate' in item:
                                item = item.replace("startDate:", "").strip()
                                dictionary['startDate'] = item
                            elif "quantity" in item:
                                item = float(item.replace("quantity:", "").replace("mg/dL", "").strip())
                                dictionary['quantity'] = item
                                dictionary['quantity_units'] = "mg/dL"
                        retrospective_glucose_effect_list.append(dictionary)
                    loop_report_dict["retrospective_glucose_effect"] = retrospective_glucose_effect_list
                except Exception as e:
                    logger.debug("handled error loop data manager - retrospective_glucose_effect")
                    logger.debug(e)

                try:
                    glucose_momentum_effect = loop_data_manager['glucoseMomentumEffect']
                    glucose_momentum_effect = glucose_momentum_effect.replace("[", "").replace("]", "").replace("LoopKit.GlucoseEffect(", "")
                    values = glucose_momentum_effect.split(")")
                    values.pop(len(values) - 1)
                    glucose_momentum_effect_list = []
                    for value in values:
                        items = value.split(",")
                        dictionary = {}

                        for item in items:
                            if 'startDate' in item:
                                item = item.replace("startDate:", "").strip()
                                dictionary['startDate'] = item
                            elif "quantity" in item:
                                item = float(item.replace("quantity:", "").replace("mg/dL", "").strip())
                                dictionary['quantity'] = item
                                dictionary['quantity_units'] = "mg/dL"
                        glucose_momentum_effect_list.append(dictionary)
                    loop_report_dict["glucose_momentum_effect"] = glucose_momentum_effect_list
                except Exception as e:
                    logger.debug("handled error loop data manager - glucose_momentum_effect")
                    logger.debug(e)

                try:
                    retrospective_glucose_change = loop_data_manager['retrospectiveGlucoseChange']
                    retrospective_glucose_change = retrospective_glucose_change.replace("Optional((", "").replace("))", "")
                    split_index = retrospective_glucose_change.index('end')
                    start = retrospective_glucose_change[:split_index]
                    start = start.replace("start: LoopKit.StoredGlucoseSample(", "").replace(")", "")
                    start_list = start.split(",")
                    start_list.pop(len(start_list) - 1)
                    start_dict = {}
                    for v in start_list:
                        aux = v.split(": ")
                        start_dict[aux[0]] = aux[1]

                    end = retrospective_glucose_change[split_index:]
                    end = end.replace("end: LoopKit.StoredGlucoseSample(", "").replace(")", "")
                    end_list= end.split(",")
                    end_dict = {}
                    for v in end_list:
                        aux = v.split(": ")
                        end_dict[aux[0]] = aux[1]

                    retrospective_glucose_change_dict = {}
                    retrospective_glucose_change_dict['start_dict'] = start_dict
                    retrospective_glucose_change_dict['end_dict'] = end_dict
                    loop_report_dict["retrospective_glucose_change"] = retrospective_glucose_change_dict
                except Exception as e:
                    logger.debug("handled error loop data manager - retrospective_glucose_change")
                    logger.debug(e)

                try:
                    retrospective_predicted_glucose = loop_data_manager['retrospectivePredictedGlucose']
                    retrospective_predicted_glucose = retrospective_predicted_glucose.replace("[", "").replace("]", "").replace("LoopKit.PredictedGlucoseValue(", "")
                    values = retrospective_predicted_glucose.split(")")
                    values.pop(len(values) - 1)
                    retrospective_predicted_glucose_list = []
                    for value in values:
                        items = value.split(",")
                        dictionary = {}

                        for item in items:
                            if 'startDate' in item:
                                item = item.replace("startDate:", "").strip()
                                dictionary['startDate'] = item
                            elif "quantity" in item:
                                item = float(item.replace("quantity:", "").replace("mg/dL", "").strip())
                                dictionary['quantity'] = item
                                dictionary['quantity_units'] = "mg/dL"
                        retrospective_predicted_glucose_list.append(dictionary)

                    loop_report_dict["retrospective_predicted_glucose"] = retrospective_predicted_glucose_list
                except Exception as e:
                    logger.debug("handled error loop data manager - retrospective_predicted_glucose")
                    logger.debug(e)

                try:
                    loop_report_dict["maximum_basal_rate"] = float(
                        re.search(
                            r"maximumBasalRatePerHour: Optional\((.+?)\), maximumBolus",
                            loop_data_manager["settings"],
                        ).group(1)
                    )
                except Exception as e:
                    logger.debug("handled error loop data manager")
                    logger.debug(e)
                try:
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
                except Exception as e:
                    logger.debug("handled error LOOP_DATA_MANAGER - retrospective_correction_enabled")
                    logger.debug(e)

                try:
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
                except Exception as e:
                    logger.debug("handled error LOOP_DATA_MANAGER - suspend_threshold_unit")
                    logger.debug(e)

                try:
                    glucoseTargetRangeSchedule_index = loop_data_manager["settings"].index("glucoseTargetRangeSchedule")
                    temp_str = loop_data_manager["settings"][glucoseTargetRangeSchedule_index:]
                    items_index = temp_str.index("items")
                    temp_str = temp_str[items_index:]
                    temp_str = temp_str.replace('items":', '')
                    values = []

                    while True:
                        if "]]" in temp_str:
                            end_index = temp_str.index("]]")
                            parse_string = temp_str[:end_index + 2]
                            item = self._parse_item(parse_string)
                            if item:
                                values.append(item)
                            else:
                                break
                            temp_str = temp_str[end_index+3:]
                        else:
                            break

                    loop_report_dict["correction_range_schedule"] = values

                except Exception as e:
                    print("correction_range_schedule missing in file : " + file_name)
                    logger.debug("handled error LOOP_DATA_MANAGER - glucose_target_range_schedule")
                    logger.debug(e)

                try:
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
                    workout_list = eval(
                        substr[start_index : workout + 1]
                    )
                    if workout_list[0] < workout_list[1]:
                        loop_report_dict["override_range_workout_minimum"] = workout_list[0]
                        loop_report_dict["override_range_workout_maximum"] = workout_list[1]
                    else:
                        loop_report_dict["override_range_workout_minimum"] = workout_list[1]
                        loop_report_dict["override_range_workout_maximum"] = workout_list[0]

                except Exception as e:
                    logger.debug("handled error LOOP_DATA_MANAGER - override_range_workout")
                    logger.debug(e)

                try:
                    premeal = substr.index("preMeal")
                    start_index = premeal + 10
                    check = ""

                    while check != "]":
                        premeal += 1
                        check = substr[premeal]


                    premeal_list = eval(
                        substr[start_index : premeal + 1]
                    )
                    if premeal_list[0] < premeal_list[1]:
                        loop_report_dict["override_range_premeal_minimum"] = premeal_list[0]
                        loop_report_dict["override_range_premeal_maximum"] = premeal_list[1]
                    else:
                        loop_report_dict["override_range_premeal_minimum"] = premeal_list[1]
                        loop_report_dict["override_range_premeal_maximum"] = premeal_list[0]

                except Exception as e:
                    logger.debug("preMeal is not in loop data")
                    logger.debug(e)

            except Exception as e:
                logger.debug("handled error loop data manager")
                logger.debug(e)

        if Sections.INSULIN_COUNTERACTION_EFFECTS in dict:
            try:
                ice_list = dict[Sections.INSULIN_COUNTERACTION_EFFECTS]
                ice_list.pop(0)
                ice_list.pop(len(ice_list) - 1)
                temp_list = []
                for items in ice_list:
                    start, end, value = items.split(",")
                    temp_dict = {
                        "start_time": start,
                        "end_time": end,
                        "value": float(value),
                        "units": "mg/dL/min",
                    }
                    temp_list.append(temp_dict)
                loop_report_dict["insulin_counteraction_effects"] = temp_list

            except Exception as e:
                logger.debug("handled error INSULIN_COUNTERACTION_EFFECTS")
                logger.debug(e)

        if Sections.RETROSPECTIVE_GLUCOSE_DISCREPANCIES_SUMMED in dict:
            try:
                local_list = dict[Sections.RETROSPECTIVE_GLUCOSE_DISCREPANCIES_SUMMED]
                local_list.pop(0)
                local_list.pop(len(local_list) - 1)
                temp_list = []
                for items in local_list:
                    start, end, value = items.split(",")
                    temp_dict = {
                        "start_time": start,
                        "end_time": end,
                        "value": float(value),
                        "units": "mg/dL",
                    }
                    temp_list.append(temp_dict)

                loop_report_dict[
                    "retrospective_glucose_discrepancies_summed"
                ] = temp_list

            except Exception as e:
                logger.debug("handled error RETROSPECTIVE_GLUCOSE_DISCREPANCIES")
                logger.debug(e)

        if Sections.GET_RESERVOIR_VALUES in dict:
            try:
                local_list = dict[Sections.GET_RESERVOIR_VALUES]
                local_list.pop(0)
                local_list.pop(len(local_list) - 1)
                temp_list = []
                for items in local_list:
                    start, value = items.split(",")

                    temp_dict = {
                        "start_time": start,
                        "value": float(value),
                        "units": "unitVolume",
                    }
                    temp_list.append(temp_dict)

                loop_report_dict["get_reservoir_values"] = temp_list

            except Exception as e:
                logger.debug("handled error GET_RESERVOIR_VALUES")
                logger.debug(e)

        if Sections.PREDICTED_GLUCOSE in dict:
            try:
                local_list = dict[Sections.PREDICTED_GLUCOSE]
                local_list.pop(0)
                local_list.pop(len(local_list) - 1)
                temp_list = []
                for items in local_list:
                    start, value = items.split(",")
                    temp_dict = {
                        "start_time": start,
                        "value": float(value),
                        "units": "mg/dL",
                    }
                    temp_list.append(temp_dict)

                loop_report_dict["predicted_glucose"] = temp_list

            except Exception as e:
                logger.debug("handled error PREDICTED_GLUCOSE")
                logger.debug(e)

        if Sections.RETROSPECTIVE_GLUCOSE_DISCREPANCIES in dict:
            try:
                local_list = dict[Sections.RETROSPECTIVE_GLUCOSE_DISCREPANCIES]
                local_list.pop(0)
                local_list.pop(len(local_list) - 1)
                temp_list = []

                for items in local_list:
                    start, value = items.split(",")
                    temp_dict = {
                        "start_time": start,
                        "value": float(value),
                        "units": "mg/dL",
                    }
                    temp_list.append(temp_dict)

                loop_report_dict["retrospective_glucose_discrepancies"] = temp_list

            except Exception as e:
                logger.debug("handled error RETROSPECTIVE_GLUCOSE_DISCREPANCIES")
                logger.debug(e)

        if Sections.CARB_EFFECT in dict:
            try:
                local_list = dict[Sections.CARB_EFFECT]
                local_list.pop(0)
                local_list.pop(len(local_list) - 1)
                temp_list = []
                for items in local_list:
                    start, value = items.split(",")
                    temp_dict = {
                        "start_time": start,
                        "value": float(value),
                        "units": "mg/dL",
                    }
                    temp_list.append(temp_dict)
                loop_report_dict["carb_effect"] = temp_list

            except Exception as e:
                logger.debug("handled error CARB_EFFECT")
                logger.debug(e)

        if Sections.INSULIN_EFFECT in dict:
            try:
                local_list = dict[Sections.INSULIN_EFFECT]
                local_list.pop(0)
                local_list.pop(len(local_list) - 1)
                temp_list = []
                for item in local_list:
                    start, value = item.split(",")
                    temp_dict = {
                        "start_time": start,
                        "value": float(value),
                        "units": "mg/dL",
                    }
                    temp_list.append(temp_dict)

                loop_report_dict["insulin_effect"] = temp_list

            except Exception as e:
                logger.debug("handled error INSULIN_EFFECT")
                logger.debug(e)

        if Sections.GET_NORMALIZED_PUMP_EVENT_DOSE in dict:
            try:
                local_list = dict[Sections.GET_NORMALIZED_PUMP_EVENT_DOSE]
                temp_list = []
                for item in local_list:
                    record_dict = {}
                    item = item.replace("DoseEntry(", "")
                    item = item.replace(item[len(item) - 1], "")
                    item = item.replace("Optional(", "")
                    key_value = item.split(", ")

                    for v in key_value:
                        aux = v.split(": ")
                        if "scheduledBasalRate" in v:
                            if "IU/hr" in aux[1]:
                                aux[1] = float(aux[1].replace("IU/hr", "").strip())

                        record_dict[aux[0]] = aux[1]
                    record_dict["scheduledBasalRate"] = "IU/hr"
                    temp_list.append(record_dict)

                loop_report_dict["get_normalized_pump_event_dose"] = temp_list
            except Exception as e:
                logger.debug("handled error GET_NORMALIZED_PUMP_EVENT_DOSE")
                logger.debug(e)

        if Sections.GET_NORMALIZED_DOSE_ENTRIES in dict:
            try:
                local_list = dict[Sections.GET_NORMALIZED_DOSE_ENTRIES]
                temp_list = []
                for item in local_list:
                    record_dict = {}
                    item = item.replace("DoseEntry(", "")
                    item = item.replace(item[len(item) - 1], "")
                    item = item.replace("Optional(", "")
                    key_value = item.split(", ")

                    for v in key_value:
                        aux = v.split(": ")
                        record_dict[aux[0]] = aux[1]
                    temp_list.append(record_dict)

                loop_report_dict["get_normalized_dose_entries"] = temp_list

            except Exception as e:
                logger.debug("handled error GET_NORMALIZED_DOSE_ENTRIES")
                logger.debug(e)

        if Sections.CACHED_DOSE_ENTRIES in dict:
            try:
                local_list = dict[Sections.CACHED_DOSE_ENTRIES]
                temp_list = []
                for item in local_list:
                    record_dict = {}
                    item = item.replace("DoseEntry(", "")
                    item = item.replace(item[len(item) - 1], "")
                    item = item.replace("Optional(", "")
                    key_value = item.split(", ")

                    for v in key_value:
                        aux = v.split(": ")
                        if 'scheduledBasalRate' in aux[0] and aux[1] != 'nil':
                            val = aux[1].replace('IU/hr', '')
                            record_dict[aux[0]] = float(val)
                            record_dict['scheduledBasalRateUnits'] = 'IU/hr'
                        else:
                            record_dict[aux[0]] = aux[1]
                    temp_list.append(record_dict)

                loop_report_dict["cached_dose_entries"] = temp_list
            except Exception as e:
                logger.debug("handled error CACHED_DOSE_ENTRIES")
                logger.debug(e)

        if Sections.GET_PUMP_EVENT_VALUES in dict:
            try:
                items = dict[Sections.GET_PUMP_EVENT_VALUES]
                get_pump_even_values_list = []
                for temp in items:

                    get_pump_even_values_dict = {}

                    value = "rate"
                    try:
                        start_index = temp.index(value)
                        value_temp = temp[start_index:]
                        value_temp = value_temp.replace('"', '')
                        last_index = value_temp.index(",")
                        get_pump_even_values_dict[value] = value_temp[len(value) + 1:last_index]
                    except Exception as e:
                        logger.debug("handled error GET_PUMP_EVENT_VALUES --" + value)
                        logger.debug(e)

                    value = "timeOffset"
                    try:
                        start_index = temp.index(value)
                        value_temp = temp[start_index:]
                        value_temp = value_temp.replace('"', '')
                        last_index = value_temp.index(",")
                        get_pump_even_values_dict[value] = value_temp[len(value) + 1:last_index]
                    except Exception as e:
                        logger.debug("handled error GET_PUMP_EVENT_VALUES --" + value)
                        logger.debug(e)

                    value = "index"
                    try:
                        start_index = temp.index(value)
                        value_temp = temp[start_index:]
                        value_temp = value_temp.replace('"', '')
                        last_index = value_temp.index(",")
                        get_pump_even_values_dict[value] = value_temp[len(value) + 1:last_index]
                    except Exception as e:
                        logger.debug("handled error GET_PUMP_EVENT_VALUES --" + value)
                        logger.debug(e)

                    value = "isLeapMonth"
                    try:
                        start_index = temp.index(value)
                        value_temp = temp[start_index:]
                        value_temp = value_temp.replace('"', '')
                        last_index = value_temp.index(",")
                        get_pump_even_values_dict[value] = value_temp[len(value) + 1:last_index]
                    except Exception as e:
                        logger.debug("handled error GET_PUMP_EVENT_VALUES --" + value)
                        logger.debug(e)

                    value = "timestamp"
                    try:
                        start_index = temp.index(value)
                        value_temp = temp[start_index:]
                        value_temp = value_temp.replace('"', '')
                        last_index = value_temp.index(",")
                        get_pump_even_values_dict[value] = value_temp[len(value) + 1:last_index]
                    except Exception as e:
                        logger.debug("handled error GET_PUMP_EVENT_VALUES --" + value)
                        logger.debug(e)

                    value = "rawData"
                    try:
                        start_index = temp.index(value)
                        value_temp = temp[start_index:]
                        value_temp = value_temp.replace('"', '')
                        last_index = value_temp.index(",")
                        get_pump_even_values_dict[value] = value_temp[len(value) + 1:last_index]
                    except Exception as e:
                        logger.debug("handled error GET_PUMP_EVENT_VALUES --" + value)
                        logger.debug(e)

                    value = "length"
                    try:
                        start_index = temp.index(value)
                        value_temp = temp[start_index:]
                        value_temp = value_temp.replace('"', '')
                        last_index = value_temp.index(",")
                        get_pump_even_values_dict[value] = value_temp[len(value) + 1:last_index]
                    except Exception as e:
                        logger.debug("handled error GET_PUMP_EVENT_VALUES --" + value)
                        logger.debug(e)

                    value = "raw"
                    try:
                        start_index = temp.index(value)
                        value_temp = temp[start_index:]
                        value_temp = value_temp.replace('"', '')
                        last_index = value_temp.index(",")
                        get_pump_even_values_dict[value] = value_temp[len(value) + 1:last_index]
                    except Exception as e:
                        logger.debug("handled error GET_PUMP_EVENT_VALUES --" + value)
                        logger.debug(e)

                    value = "objectIDURL"
                    try:
                        start_index = temp.index(value)
                        value_temp = temp[start_index:]
                        value_temp = value_temp.replace('"', '')
                        last_index = value_temp.index(",")
                        get_pump_even_values_dict[value] = value_temp[len(value) + 1:last_index]
                    except Exception as e:
                        logger.debug("handled error GET_PUMP_EVENT_VALUES --" + value)
                        logger.debug(e)

                    value = "isUploaded"
                    try:
                        start_index = temp.index(value)
                        value_temp = temp[start_index:]
                        value_temp = value_temp.replace('"', '')
                        last_index = value_temp.index(",")
                        get_pump_even_values_dict[value] = value_temp[len(value) + 1:last_index]
                    except Exception as e:
                        logger.debug("handled error GET_PUMP_EVENT_VALUES --" + value)
                        logger.debug(e)

                    #todo: need to parse this out more
                    value = "syncIdentifier"
                    try:
                        start_index = temp.index(value)
                        value_temp = temp[start_index:]
                        value_temp = value_temp.replace('"', '')
                        last_index = value_temp.index(")),")
                        get_pump_even_values_dict[value] = value_temp[len(value) + 1:last_index]
                    except Exception as e:
                        logger.debug("handled error GET_PUMP_EVENT_VALUES --" + value)
                        logger.debug(e)

                    value = "description"
                    try:
                        start_index = temp.index(value)
                        value_temp = temp[start_index:]
                        value_temp = value_temp.replace('"', '')
                        last_index = value_temp.index(",")
                        get_pump_even_values_dict[value] = value_temp[len(value) + 1:last_index]
                    except Exception as e:
                        logger.debug("handled error GET_PUMP_EVENT_VALUES --" + value)
                        logger.debug(e)

                    value = "unit"
                    try:
                        start_index = temp.index(value)
                        value_temp = temp[start_index:]
                        value_temp = value_temp.replace('"', '')
                        last_index = value_temp.index(",")
                        get_pump_even_values_dict[value] = value_temp[len(value) + 1:last_index]
                    except Exception as e:
                        logger.debug("handled error GET_PUMP_EVENT_VALUES --" + value)
                        logger.debug(e)

                    value = "value"
                    try:
                        start_index = temp.index(value)
                        value_temp = temp[start_index:]
                        value_temp = value_temp.replace('"', '')
                        last_index = value_temp.index(",")
                        get_pump_even_values_dict[value] = value_temp[len(value) + 1:last_index]
                    except Exception as e:
                        logger.debug("handled error GET_PUMP_EVENT_VALUES --" + value)
                        logger.debug(e)

                    value = "endDate"
                    try:
                        start_index = temp.index(value)
                        value_temp = temp[start_index:]
                        value_temp = value_temp.replace('"', '')
                        last_index = value_temp.index(",")
                        get_pump_even_values_dict[value] = value_temp[len(value) + 1:last_index]
                    except Exception as e:
                        logger.debug("handled error GET_PUMP_EVENT_VALUES --" + value)
                        logger.debug(e)

                    value = "startDate"
                    try:
                        start_index = temp.index(value)
                        value_temp = temp[start_index:]
                        value_temp = value_temp.replace('"', '')
                        last_index = value_temp.index(",")
                        get_pump_even_values_dict[value] = value_temp[len(value) + 1:last_index]
                    except Exception as e:
                        logger.debug("handled error GET_PUMP_EVENT_VALUES --" + value)
                        logger.debug(e)

                    value = "type"
                    try:
                        start_index = temp.index(value)
                        value_temp = temp[start_index:]
                        value_temp = value_temp.replace('"', '')
                        last_index = value_temp.index(",")
                        get_pump_even_values_dict[value] = value_temp[len(value) + 1:last_index]
                    except Exception as e:
                        logger.debug("handled error GET_PUMP_EVENT_VALUES --" + value)
                        logger.debug(e)

                    value = "type"
                    try:
                        start_index = temp.index(value)
                        value_temp = temp[start_index:]
                        value_temp = value_temp.replace('"', '')
                        last_index = value_temp.index(",")
                        get_pump_even_values_dict[value] = value_temp[len(value) + 1:last_index]
                    except Exception as e:
                        logger.debug("handled error GET_PUMP_EVENT_VALUES --" + value)
                        logger.debug(e)

                    try:
                        value = "persistedDate"
                        start_index = temp.index(value)
                        value_temp = temp[start_index:]
                        value_temp = value_temp.replace('"', '')
                        last_index = value_temp.index(",")
                        get_pump_even_values_dict[value] = value_temp[len(value) + 1:last_index]
                    except Exception as e:
                        logger.debug("handled error GET_PUMP_EVENT_VALUES --" + value)
                        logger.debug(e)

                    try:
                        value = "date"
                        start_index = temp.index(value)
                        value_temp = temp[start_index:]
                        value_temp = value_temp.replace('"', '')
                        last_index = value_temp.index(",")
                        get_pump_even_values_dict[value] = value_temp[len(value)+1:last_index]
                    except Exception as e:
                        logger.debug("handled error GET_PUMP_EVENT_VALUES --" + value)
                        logger.debug(e)
                    get_pump_even_values_list.append(get_pump_even_values_dict)

                loop_report_dict["get_pump_event_values"] = get_pump_even_values_list

            except Exception as e:
                logger.debug("handled error GET_PUMP_EVENT_VALUES")
                logger.debug(e)

        if Sections.MESSAGE_LOG in dict:
            local_list = dict[Sections.MESSAGE_LOG]
            loop_report_dict["message_log"] = local_list

        if Sections.G5_CGM_MANAGER in dict:
            try:
                temp_dict = dict[Sections.G5_CGM_MANAGER]
                cgmblekit = temp_dict["latestReading"]
                cgmblekit = cgmblekit.replace(
                    "Optional(CGMBLEKit.Glucose(glucoseMessage: CGMBLEKit.GlucoseSubMessage(",
                    "",
                )
                cgmblekit = cgmblekit.replace("))", "")

                split_list = cgmblekit.split(",")

                dictionary_complete = {}

                if "transmitter" in temp_dict:
                    dictionary_complete["transmitter"] = temp_dict["transmitter"]

                if "providesBLEHeartbeat" in temp_dict:
                    dictionary_complete["providesBLEHeartbeat"] = temp_dict[
                        "providesBLEHeartbeat"
                    ]
                dictionary = {}
                timeMessage = {}
                glucoseMessage = {}
                latestReading = {}
                for item in split_list:
                    if "timeMessage:" in item:
                        item = item.replace(
                            "timeMessage: CGMBLEKit.TransmitterTimeRxMessage(", ""
                        )
                        keyvalue = item.split(":")
                        timeMessage["status"] = keyvalue[1].strip("\"'")

                    else:
                        item = item.replace(")", "")
                        keyvalue = item.split(":")
                        m = keyvalue[0].strip("'")
                        m = m.replace('"', "").strip()
                        dictionary[m] = keyvalue[1].strip("\"'")

                glucoseMessage["timestamp"] = dictionary["timestamp"]
                glucoseMessage["glucoseIsDisplayOnly"] = dictionary[
                    "glucoseIsDisplayOnly"
                ]
                glucoseMessage["glucose"] = dictionary["glucose"]
                glucoseMessage["trend"] = dictionary["trend"]

                timeMessage["currentTime"] = dictionary["currentTime"]
                timeMessage["sessionStartTime"] = dictionary["sessionStartTime"]

                latestReading["glucoseMessage"] = glucoseMessage
                latestReading["timeMessage"] = timeMessage
                latestReading["transmitterID"] = dictionary["transmitterID"]
                latestReading["status"] = dictionary["status"]
                latestReading["sessionStartDate"] = dictionary["sessionStartDate"]
                latestReading["lastCalibration"] = dictionary["lastCalibration"]
                latestReading["readDate"] = dictionary["readDate"]

                dictionary_complete["latestReading"] = latestReading

                loop_report_dict["g5_cgm_manager"] = dictionary_complete
            except Exception as e:
                logger.debug("handled error G5_CGM_MANAGER")
                logger.debug(e)

        if Sections.DEX_CGM_MANAGER in dict:
            try:
                temp_dict = dict[Sections.DEX_CGM_MANAGER]
                temp_string = temp_dict["latestBackfill"]
                temp_string = temp_string.replace(
                    " Optional(ShareClient.ShareGlucose(", ""
                )
                temp_string = temp_string.replace("))", "")
                temp_list = temp_string.split(",")
                dictionary = {}
                for item in temp_list:
                    self.add_to_dictionary(dictionary, item)

                latestBackfill = {}
                latestBackfill["latestBackfill"] = dictionary

                loop_report_dict["dex_cgm_manager"] = latestBackfill

            except Exception as e:
                logger.debug("handled error DEX_CGM_MANAGER")
                logger.debug(e)

        if Sections.STATUS_EXTENSION_DATA_MANAGER in dict:
            try:
                status_extension_data_manager = dict[
                    Sections.STATUS_EXTENSION_DATA_MANAGER
                ]
                status_extension_context_dict = {}

                predicted_glucose = {}

                temp = status_extension_data_manager["statusExtensionContext"]
                temp = temp.replace("Optional([", "")
                values_index = temp.index("values")
                values_temp = temp[values_index:]
                last_index = values_temp.index("]")
                values = values_temp[:last_index+1]
                values = values.replace(": [", "")
                values = values.replace("values", "")
                values = values.replace("]", "")
                values = values.replace(', "', "")
                values = values.replace('"', "")
                values = values.replace(' ', "")
                values_list = values.split(",")
                predicted_glucose["values"] = values_list

                try:
                    sensor_index = temp.index("sensor")
                    sensor_temp = temp[sensor_index:]
                    last_index = sensor_temp.index("]")
                    sensor = sensor_temp[9:last_index+1]
                    sensor = sensor.replace('"', "")
                    sensor = sensor.replace('[', "").replace(']', "")
                    sensor = sensor.strip()
                    temp_list = sensor.split(",")
                    value_dict = {}
                    for value in temp_list:
                        val = value.split(":")
                        value_dict[val[0]] = val[1]
                        '"85.732078872579'
                    status_extension_context_dict["sensor"] = value_dict
                except Exception as e:
                    logger.debug("handled error STATUS_EXTENSION_DATA_MANAGER - sensor")
                    logger.debug(e)


                try:
                    netBasal_index = temp.index("netBasal")
                    netBasal_temp = temp[netBasal_index:]
                    last_index = netBasal_temp.index("]")
                    netBasal = netBasal_temp[9:last_index+1]
                    netBasal = netBasal.replace('[', "").replace(']', "")
                    netBasal = netBasal.strip()
                    temp_list = netBasal.split(",")
                    value_dict = {}
                    for value in temp_list:
                        val = value.split(":")
                        value_dict[val[0]] = val[1]
                    status_extension_context_dict["netBasal"] = value_dict
                except Exception as e:
                    logger.debug("handled error STATUS_EXTENSION_DATA_MANAGER - netBasal")
                    logger.debug(e)

                try:
                    version_index = temp.index("version")
                    version_temp = temp[version_index:]
                    last_index = version_temp.index(",")
                    status_extension_context_dict["version"] = version_temp[10:last_index]
                except Exception as e:
                    logger.debug("handled error STATUS_EXTENSION_DATA_MANAGER - version")
                    logger.debug(e)

                try:
                    unit_index = temp.index("unit")
                    unit_temp = temp[unit_index:]
                    unit_temp = unit_temp.replace('"', '')
                    last_index = unit_temp.index(",")
                    predicted_glucose["unit"] = unit_temp[6:last_index]
                except Exception as e:
                    logger.debug("handled error STATUS_EXTENSION_DATA_MANAGER - unit")
                    logger.debug(e)

                try:
                    interval_index = temp.index("interval")
                    interval_temp = temp[interval_index:]
                    interval_temp = interval_temp.replace('"', '')
                    last_index = interval_temp.index(",")
                    interval_temp = interval_temp[9:last_index].replace("]", "")
                    predicted_glucose["interval"] = float(interval_temp)
                except Exception as e:
                    logger.debug("handled error STATUS_EXTENSION_DATA_MANAGER - interval")
                    logger.debug(e)

                try:
                    startDate_index = temp.index("startDate")
                    startDate_temp = temp[startDate_index:]
                    startDate_temp = startDate_temp.replace('"', '')
                    last_index = startDate_temp.index(",")
                    predicted_glucose["startDate"] = startDate_temp[10:last_index]
                except Exception as e:
                    logger.debug("handled error STATUS_EXTENSION_DATA_MANAGER - startDate")
                    logger.debug(e)

                status_extension_context_dict["predictedGlucose"] = predicted_glucose

                try:
                    batteryPercentage_index = temp.index("batteryPercentage")
                    batteryPercentage_temp = temp[batteryPercentage_index:]
                    batteryPercentage_temp = batteryPercentage_temp.replace('"', '')
                    last_index = batteryPercentage_temp.index(",")
                    status_extension_context_dict["batteryPercentage"] = float(batteryPercentage_temp[18:last_index].strip())
                except Exception as e:
                    logger.debug("handled error STATUS_EXTENSION_DATA_MANAGER - batteryPercentage")
                    logger.debug(e)

                try:
                    lastLoopCompleted_index = temp.index("lastLoopCompleted")
                    lastLoopCompleted_temp = temp[lastLoopCompleted_index:]
                    lastLoopCompleted_temp = lastLoopCompleted_temp.replace('"', '')
                    last_index = lastLoopCompleted_temp.index(",")
                    status_extension_context_dict["lastLoopCompleted"] = lastLoopCompleted_temp[18:last_index]
                except Exception as e:
                    logger.debug("handled error STATUS_EXTENSION_DATA_MANAGER - lastLoopCompleted")
                    logger.debug(e)


                loop_report_dict["status_extension_data_manager"] = status_extension_context_dict
            except Exception as e:
                logger.debug("handled error STATUS_EXTENSION_DATA_MANAGER")
                logger.debug(e)

        if Sections.RILEY_LINK_PUMP_MANAGER in dict:
            try:
                loop_report_dict["riley_link_pump_manager"] = dict[
                    Sections.RILEY_LINK_PUMP_MANAGER
                ]
            except Exception as e:
                logger.debug("handled error RILEY_LINK_PUMP_MANAGER")
                logger.debug(e)

        if Sections.RILEY_LINK_DEVICE_MANAGER in dict:
            try:
                loop_report_dict["riley_link_device_manager"] = dict[
                    Sections.RILEY_LINK_DEVICE_MANAGER
                ]
            except Exception as e:
                logger.debug("handled error RILEY_LINK_DEVICE_MANAGER")
                logger.debug(e)

        if Sections.PERSISTENCE_CONTROLLER in dict:
            try:
                loop_report_dict["persistence_controller"] = dict[
                    Sections.PERSISTENCE_CONTROLLER
                ]
            except Exception as e:
                logger.debug("handled error PERSISTENCE_CONTROLLER")
                logger.debug(e)

        if Sections.INSULIN_DELIVERY_STORE in dict:
            try:
                loop_report_dict["insulin_delivery_store"] = dict[
                    Sections.INSULIN_DELIVERY_STORE
                ]
            except Exception as e:
                logger.debug("handled error INSULIN_DELIVERY_STORE")
                logger.debug(e)

        if Sections.CACHED_CARB_ENTRIES in dict:
            try:
                temp_list = []
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
                    if isinstance(quantity, str):
                        quantity = float(quantity.replace("g", ""))

                    record_dict = {
                        "sampleUUID": sampleUUID,
                        "syncIdentifier": syncIdentifier,
                        "syncVersion": syncVersion,
                        "startDate": startDate,
                        "quantity": quantity,
                        "quantity_units": "g",
                        "foodType": foodType,
                        "absorptionTime": absorptionTime,
                        "createdByCurrentApp": createdByCurrentApp,
                        "externalID": externalID,
                        "isUploaded": isUploaded,
                    }
                    temp_list.append(record_dict)
                loop_report_dict["cached_carb_entries"] = temp_list
            except Exception as e:
                logger.debug("handled error CACHED_CARB_ENTRIES")
                logger.debug(e)

        if Sections.GLUCOSE_STORE in dict:
            try:
                temp_dict = dict[Sections.GLUCOSE_STORE]
                latest_glucose_value = temp_dict["latestGlucoseValue"]
                latest_glucose_value = latest_glucose_value.replace(
                    "Optional(LoopKit.StoredGlucoseSample(", ""
                )
                latest_glucose_value = latest_glucose_value.replace("))", "")
                latest_glucose_value = latest_glucose_value.split(",")

                dictionary = {}
                for item in latest_glucose_value:
                    if "startDate" in item:
                        value = item.replace("startDate: ", "")
                        dictionary["startDate"] = value
                    elif "quantity" in item:
                        value = item.replace("quantity: ", "")
                        if "mg/dL" in value:
                            value = float(value.replace("mg/dL", "").strip())
                        dictionary["quantity"] = value
                        dictionary["quantity_units"] = "mg/dL"
                    else:
                        self.add_to_dictionary(dictionary, item)

                temp_dict["latestGlucoseValue"] = dictionary
                loop_report_dict["glucose_store"] = temp_dict

            except Exception as e:
                logger.debug("handled error GLUCOSE_STORE")
                logger.debug(e)

        if Sections.CACHED_GLUCOSE_SAMPLES in dict:
            try:
                local_list = dict[Sections.CACHED_GLUCOSE_SAMPLES]
                temp_list = []
                for item in local_list:
                    record_dict = {}
                    item = item.replace("StoredGlucoseSample(", "")
                    item = item.replace(item[len(item) - 1], "")
                    key_value = item.split(", ")

                    for v in key_value:
                        aux = v.split(": ")
                        if aux[0] == "quantity":
                            if isinstance(aux[1], str) and "mg/dL" in aux[1]:
                                aux[1] = float(aux[1].replace("mg/dL", ""))
                        record_dict[aux[0]] = aux[1]
                    record_dict["quantity_units"] = "mg/dL"
                    temp_list.append(record_dict)

                loop_report_dict["cached_glucose_samples"] = temp_list
            except Exception as e:
                logger.debug("handled error CACHED_GLUCOSE_SAMPLES")
                logger.debug(e)

        return loop_report_dict

    def add_to_dictionary(self, dictionary, item):
        keyvalue = item.split(":")
        m = keyvalue[0].strip("'")
        if m.isdigit():
            if "." in m:
                m = float(m)
            else:
                m = int(m)

        m = m.replace("]", "").strip()
        dictionary[m] = keyvalue[1].strip("\"'").replace("]", "")

    def __set_pump_manager_type(
        self, loop_report_dict, minimed_pump_manager, omnipod_pump_manager
    ):
        if minimed_pump_manager:
            loop_report_dict["pump_manager_type"] = "minimed"
            try:
                loop_report_dict["pump_model"] = minimed_pump_manager[
                    "pumpModel"
                ].strip()
            except Exception as e:
                logger.debug("pump model in minimed_pump_manager is not available")
                logger.debug(e)

        elif omnipod_pump_manager:
            loop_report_dict["pump_manager_type"] = "omnipod"
            try:
                loop_report_dict["pm_version"] = omnipod_pump_manager[
                    "pmVersion"
                ].strip()
                loop_report_dict["pi_version"] = omnipod_pump_manager[
                    "piVersion"
                ].strip()
            except Exception as e:
                logger.debug(
                    "pm version or pi version in omnipod_pump_manager is not available"
                )
                logger.debug(e)

        else:
            loop_report_dict["pump_manager_type"] = "unknown"


    def _parse_item(self, item):
        item_dict = None
        if "startTime" in item:
            item = item.replace('[', '').replace('"', "").replace(']', "")
            items_values = item.split(",")
            item_list = []

            if 'startTime' not in items_values[0] and 'value:' not in items_values[0]:
                items_values.pop(0)

            if 'value:' in items_values[0]:
                item_list = [float(items_values[0].replace('value:', '').strip()),
                             float(items_values[1].strip())]
                startTime = items_values[2].replace('startTime:', '').strip()
            else:
                startTime = items_values[0].replace('startTime:', '').strip()
                item_list = [float(items_values[1].replace('value:', '').strip()),
                             float(items_values[2].strip())]

            item_dict = {'startTime': startTime,
                         'value': item_list}
        return item_dict
