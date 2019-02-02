"""
description: A parser to parse the default loop report obtained from loop iphone application. Converts the readme
sections and lines into high level dictionaries and list objects.

author: Russell Wilson
dependencies:
* <>
license: BSD-2-Clause
"""


class Sections:
    LOOP_VERSION = "loop_version"
    DEVICE_DATA_MANAGER = "device_data_manager"
    RILEY_LINK_DEVICE = "riley_link_device"
    CARB_STORE = "carb_store"
    DOSE_STORE = "dose_store"
    MINIMED_PUMP_MANAGER = "minimed_pump_manager"
    OMNIPOD_PUMP_MAANGER = "omnipod_pump_manager"
    WATCH_DATA_MANAGER = "watch_data_manager"
    LOOP_DATA_MANAGER = "loop_data_manager"


def _split_key_value(line, separator):
    end_loc = line.find(separator)
    key = line[0:end_loc]
    value = line[end_loc + 1 : len(line)]
    return key, value


def parse_loop_report(dataPathAndName):
    current_section = ""
    all_sections = {}
    new_line = False

    with open(dataPathAndName, "r") as reader:
        for line in reader:
            if line.startswith("Generated:"):
                key, value = _split_key_value(line, ":")
                generated = {}
                generated[key] = value
                all_sections["generated"] = generated
                new_line = False

            elif line.startswith("Loop"):
                key, value = _split_key_value(line, ":")
                loop = {}
                loop["loop_version"] = key
                all_sections["loop_version"] = loop
                new_line = False

            elif line.startswith("## DeviceDataManager"):
                device_data_manager = {}
                current_section = "device_data_manager"
                all_sections["device_data_manager"] = device_data_manager
                new_line = False

            elif line.startswith("## G5CGMManager"):
                g5_cgm_manager = {}
                current_section = "g5_cgm_manager"
                all_sections["g5_cgm_manager"] = g5_cgm_manager
                new_line = False

            elif line.startswith("## DexCGMManager"):
                dex_cgm_manager = {}
                current_section = "dex_cgm_manager"
                all_sections["dex_cgm_manager"] = dex_cgm_manager
                new_line = False

            elif line.startswith("## MinimedPumpManager"):
                minimed_pump_manager = {}
                current_section = "minimed_pump_manager"
                all_sections["minimed_pump_manager"] = minimed_pump_manager
                new_line = False

            elif line.startswith("## RileyLinkPumpManager"):
                riley_link_pump_manager = {}
                current_section = "riley_link_pump_manager"
                all_sections["riley_link_pump_manager"] = riley_link_pump_manager
                new_line = False

            elif line.startswith("## RileyLinkDeviceManager"):
                riley_link_device_manager = {}
                current_section = "riley_link_device_manager"
                all_sections["riley_link_device_manager"] = riley_link_device_manager
                new_line = False

            elif line.startswith("## RileyLinkDevice"):
                riley_link_device = {}
                current_section = "riley_link_device"
                all_sections["riley_link_device"] = riley_link_device
                new_line = False

            elif line.startswith("## StatusExtensionDataManager"):
                status_extension_data_manager = {}
                current_section = "status_extension_data_manager"
                all_sections[
                    "status_extension_data_manager"
                ] = status_extension_data_manager
                new_line = False

            elif line.startswith("## LoopDataManager"):
                loop_data_manager = {}
                current_section = "loop_data_manager"
                all_sections["loop_data_manager"] = loop_data_manager
                new_line = False

            elif line.startswith("insulinCounteractionEffects:"):
                insulin_counteraction_effects = []
                current_section = "insulin_counteraction_effects"
                all_sections[
                    "insulin_counteraction_effects"
                ] = insulin_counteraction_effects
                new_line = False

            elif line.startswith("predictedGlucose:"):
                predicted_glucose = []
                current_section = "predicted_glucose"
                all_sections["predicted_glucose"] = predicted_glucose
                new_line = False

            elif line.startswith("retrospectivePredictedGlucose"):
                retrospective_predicted_glucose = {}
                current_section = "retrospective_predicted_glucose"
                all_sections[
                    "retrospective_predicted_glucose"
                ] = retrospective_predicted_glucose
                new_line = False

            elif line.startswith("cacheStore: ## PersistenceController"):
                persistence_controller = {}
                current_section = "persistence_controller"
                all_sections["persistence_controller"] = persistence_controller
                new_line = False

            elif line.startswith("## GlucoseStore"):
                glucose_store = {}
                current_section = "glucose_store"
                all_sections["glucose_store"] = glucose_store
                new_line = False

            elif line.startswith("### cachedGlucoseSamples"):
                cached_glucose_samples = {}
                current_section = "cached_glucose_samples"
                all_sections["cached_glucose_samples"] = cached_glucose_samples
                new_line = False

            elif line.startswith("## CarbStore"):
                carb_store = {}
                current_section = "carb_store"
                all_sections["carb_store"] = carb_store
                new_line = False

            elif line.startswith("cachedCarbEntries:"):
                cached_carb_entries = {}
                current_section = "cached_carb_entries"
                all_sections["cached_carb_entries"] = cached_carb_entries
                new_line = False

            elif line.startswith("deletedCarbEntries:"):
                deleted_carb_entries = {}
                current_section = "deleted_carb_entries"
                all_sections["deleted_carb_entries"] = deleted_carb_entries
                new_line = False

            elif line.startswith("## DoseStore"):
                dose_store = {}
                current_section = "dose_store"
                all_sections["dose_store"] = dose_store
                new_line = False

            elif line.startswith("### getReservoirValues"):
                get_reservoir_values = []
                current_section = "get_reservoir_values"
                all_sections["get_reservoir_values"] = get_reservoir_values
                new_line = False

            elif line.startswith("### getPumpEventValues"):
                get_pump_event_values = []
                current_section = "get_pump_event_values"
                all_sections["get_pump_event_values"] = get_pump_event_values
                new_line = False

            elif line.startswith(
                "### getNormalizedPumpEventDoseEntriesOverlaidWithBasalEntries"
            ):
                normalized_pump_event_dose = {}
                current_section = "normalized_pump_event_dose"
                all_sections["normalized_pump_event_dose"] = normalized_pump_event_dose
                new_line = False

            elif line.startswith("### InsulinDeliveryStore"):
                insulin_delivery_store = {}
                current_section = "insulin_delivery_store"
                all_sections["insulin_delivery_store"] = insulin_delivery_store
                new_line = False

            elif line.startswith("## WatchDataManager"):
                watch_data_manager = {}
                current_section = "watch_data_manager"
                all_sections["watch_data_manager"] = watch_data_manager
                new_line = False

            elif line.startswith("## OmnipodPumpManager"):
                omnipod_pump_manager = {}
                current_section = "omnipod_pump_manager"
                all_sections["omnipod_pump_manager"] = omnipod_pump_manager
                new_line = False

            elif line.startswith("\n"):
                new_line = True

            elif (
                line.startswith("#") or line.startswith("##") or line.startswith("###")
            ):
                print(f"UNHANDLED SECTION: {line}")
                new_line = False

            else:
                if (
                    current_section == "insulin_counteraction_effects"
                    or current_section == "get_reservoir_values"
                    or current_section == "predicted_glucose"
                    or current_section == "get_pump_event_values"
                ):
                    new_line = False
                    i_list = all_sections[current_section]
                    if line.startswith("*"):
                        line = line[1:]
                    if line.startswith(" "):
                        line = line[1:]
                    if line.endswith("\n"):
                        line = line[:-1]

                    i_list.append(line)

                elif current_section:
                    new_line = False
                    dict = all_sections[current_section]
                    key, value = _split_key_value(line, ":")
                    if key or value != "\n":
                        if key.startswith("*"):
                            key = key[1:]
                        if key.startswith(" "):
                            key = key[1:]
                        if value.endswith("\n"):
                            value.replace("\n", "")
                        dict[key] = value.replace("\n", "")

    return all_sections


def list_sections_in_loop_report(file_path):
    section_list = []
    existing_sections = []
    new_line = None
    with open(file_path, "r") as reader:
        for line in reader:
            if line == "\n":
                new_line = "newline"
            elif (
                line.startswith("#") or line.startswith("##") or line.startswith("###")
            ):
                if new_line == "newline":
                    if line not in existing_sections:
                        section_list.append(line)
                        existing_sections.append(line)
            else:
                new_line = None

    return section_list
