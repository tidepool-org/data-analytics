"""
description: A parser to parse the default loop report obtained from loop iphone application. Converts the readme
sections and lines into high level dictionaries and list objects.

author: Russell Wilson
dependencies:
* <>
license: BSD-2-Clause
"""
import os

class Sections:
    G5_CGM_MANAGER = "g5_cgm_manager"
    DEX_CGM_MANAGER = "dex_cgm_manager"
    RILEY_LINK_PUMP_MANAGER = "riley_link_pump_manager"
    RILEY_LINK_DEVICE_MANAGER = "riley_link_device_manager"
    PERSISTENCE_CONTROLLER = "persistence_controller"
    GLUCOSE_STORE = "glucose_store"
    CACHED_GLUCOSE_SAMPLES = "cached_glucose_samples"
    CACHED_CARB_ENTRIES = "cached_carb_entries"
    INSULIN_DELIVERY_STORE = "insulin_delivery_store"
    LOOP_VERSION = "loop_version"
    DEVICE_DATA_MANAGER = "device_data_manager"
    RILEY_LINK_DEVICE = "riley_link_device"
    CARB_STORE = "carb_store"
    DOSE_STORE = "dose_store"
    MINIMED_PUMP_MANAGER = "minimed_pump_manager"
    OMNIPOD_PUMP_MANAGER = "omnipod_pump_manager"
    WATCH_DATA_MANAGER = "watch_data_manager"
    LOOP_DATA_MANAGER = "loop_data_manager"
    GET_RESERVOIR_VALUES = "get_reservoir_values"
    PREDICTED_GLUCOSE = "predicted_glucose"
    GET_PUMP_EVENT_VALUES = "get_pump_event_values"
    POD_COMMS = "pod_comms"
    MESSAGE_LOG = "message_log"
    POD_INFO_FAULT_EVENT = "pod_info_fault_event"
    OMNIPOD_PUMP_MANAGER_STATE = "omnipod_pump_manager_state"
    POD_STATE = "pod_state"
    INSULIN_COUNTERACTION_EFFECTS = "insulin_counteraction_effects"
    RETROSPECTIVE_GLUCOSE_DISCREPANCIES_SUMMED = (
        "retrospective_glucose_discrepancies_summed"
    )
    RETROSPECTIVE_GLUCOSE_DISCREPANCIES = "retrospective_glucose_discrepancies"
    CARB_EFFECT = "carb_effect"
    INSULIN_EFFECT = "insulin_effect"
    GET_NORMALIZED_PUMP_EVENT_DOSE = "get_normalized_pump_event_dose"
    GET_NORMALIZED_DOSE_ENTRIES = "get_normalized_dose_entries"
    CACHED_DOSE_ENTRIES = "cached_dose_entries"
    STATUS_EXTENSION_DATA_MANAGER = "status_extension_data_manager"
    INTEGRAL_RETROSPECTIVE_CORRECTION = "integral_retrospective_correction"
    G4_CGM_MANAGER = "g4_cgm_manager"

    """ 
        #not sure this one is used
        deleted_carb_entries
    """


def _split_key_value(line, separator):
    end_loc = line.find(separator)
    key = line[0:end_loc]
    value = line[end_loc + 1 : len(line)]
    return key, value


def parse_loop_report(path: str, file_name: str):
    current_section = ""
    all_sections = {}

    new_line = False
    dataPathAndName = os.path.join(path, file_name)

    try:

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

                elif line.startswith("retrospectivePredictedGlucose"):
                    parse_key_value(all_sections, line)

                elif line.startswith("glucoseMomentumEffect"):
                    parse_key_value(all_sections, line)

                elif line.startswith("retrospectiveGlucoseEffect"):
                    parse_key_value(all_sections, line)

                elif line.startswith("recommendedTempBasal"):
                    parse_key_value(all_sections, line)

                elif line.startswith("recommendedBolus"):
                    parse_key_value(all_sections, line)

                elif line.startswith("lastBolus"):
                    parse_key_value(all_sections, line)

                elif line.startswith("retrospectiveGlucoseChange"):
                    parse_key_value(all_sections, line)

                elif line.startswith("lastLoopCompleted"):
                    parse_key_value(all_sections, line)

                elif line.startswith("lastTempBasal"):
                    parse_key_value(all_sections, line)

                elif line.startswith("carbsOnBoard"):
                    parse_key_value(all_sections, line)

                elif line.startswith("error"):
                    parse_key_value(all_sections, line)

                elif line.startswith("insulinCounteractionEffects:"):
                    insulin_counteraction_effects = []
                    current_section = "insulin_counteraction_effects"
                    all_sections[
                        "insulin_counteraction_effects"
                    ] = insulin_counteraction_effects
                    new_line = False

                elif line.startswith("carbEffect:"):
                    carb_effect = []
                    current_section = "carb_effect"
                    all_sections["carb_effect"] = carb_effect
                    new_line = False

                elif line.startswith("insulinEffect:"):
                    insulin_effect = []
                    current_section = "insulin_effect"
                    all_sections["insulin_effect"] = insulin_effect
                    new_line = False

                elif line.startswith("predictedGlucose:"):
                    predicted_glucose = []
                    current_section = "predicted_glucose"
                    all_sections["predicted_glucose"] = predicted_glucose
                    new_line = False

                elif line.startswith("retrospectiveGlucoseDiscrepancies:"):
                    retrospective_glucose_discrepancies = []
                    current_section = "retrospective_glucose_discrepancies"
                    all_sections[
                        "retrospective_glucose_discrepancies"
                    ] = retrospective_glucose_discrepancies
                    new_line = False

                elif line.startswith("retrospectiveGlucoseDiscrepanciesSummed:"):
                    retrospective_glucose_discrepancies_summed = []
                    current_section = "retrospective_glucose_discrepancies_summed"
                    all_sections[
                        "retrospective_glucose_discrepancies_summed"
                    ] = retrospective_glucose_discrepancies_summed
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
                    cached_glucose_samples = []
                    current_section = "cached_glucose_samples"
                    all_sections["cached_glucose_samples"] = cached_glucose_samples
                    new_line = False

                elif line.startswith("## CarbStore"):
                    carb_store = {}
                    current_section = "carb_store"
                    all_sections["carb_store"] = carb_store
                    new_line = False

                elif line.startswith("cachedCarbEntries:"):
                    cached_carb_entries = []
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

                elif line.startswith("### getNormalizedDoseEntries"):
                    get_normalized_dose_entries = []
                    current_section = "get_normalized_dose_entries"
                    all_sections[
                        "get_normalized_dose_entries"
                    ] = get_normalized_dose_entries
                    new_line = False

                elif line.startswith(
                    "### getNormalizedPumpEventDoseEntriesOverlaidWithBasalEntries"
                ):
                    get_normalized_pump_event_dose = []
                    current_section = "get_normalized_pump_event_dose"
                    all_sections[
                        "get_normalized_pump_event_dose"
                    ] = get_normalized_pump_event_dose
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

                elif line.startswith("## G6CGMManager"):
                    g6_cgm_manager = {}
                    current_section = "g6_cgm_manager"
                    all_sections["g6_cgm_manager"] = g6_cgm_manager
                    new_line = False

                elif line.startswith("## G4CGMManager"):
                    g4_cgm_manager = {}
                    current_section = "g4_cgm_manager"
                    all_sections["g4_cgm_manager"] = g4_cgm_manager
                    new_line = False

                elif line.startswith("## IntegralRetrospectiveCorrection"):
                    integral_retrospective_correction = {}
                    current_section = "integral_retrospective_correction"
                    all_sections["integral_retrospective_correction"] = integral_retrospective_correction
                    new_line = False

                elif line.startswith("## ShareClientManager"):
                    share_client_manager = {}
                    current_section = "share_client_manager"
                    all_sections["share_client_manager"] = share_client_manager
                    new_line = False

                elif line.startswith("## PodComms"):
                    pod_comms = {}
                    current_section = "pod_comms"
                    all_sections["pod_comms"] = pod_comms
                    new_line = False

                elif line.startswith("### MessageLog"):
                    message_log = []
                    current_section = "message_log"
                    all_sections["message_log"] = message_log
                    new_line = False

                elif line.startswith("#### cachedDoseEntries"):
                    cached_dose_entries = []
                    current_section = "cached_dose_entries"
                    all_sections["cached_dose_entries"] = cached_dose_entries
                    new_line = False

                elif line.startswith("## PodInfoFaultEvent"):
                    pod_info_fault_event = {}
                    current_section = "pod_info_fault_event"
                    all_sections["pod_info_fault_event"] = pod_info_fault_event
                    new_line = False

                elif line.startswith("### OmnipodPumpManagerState"):
                    omnipod_pump_manager_state = {}
                    current_section = "omnipod_pump_manager_state"
                    all_sections["omnipod_pump_manager_state"] = omnipod_pump_manager_state
                    new_line = False

                elif line.startswith("## PodState"):
                    pod_state = {}
                    current_section = "pod_state"
                    all_sections["pod_state"] = pod_state
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
                        or current_section == "message_log"
                        or current_section == "get_normalized_dose_entries"
                        or current_section == "cached_dose_entries"
                        or current_section == "get_normalized_pump_event_dose"
                        or current_section == "insulin_effect"
                        or current_section == "carb_effect"
                        or current_section == "retrospective_glucose_discrepancies"
                        or current_section == "retrospective_glucose_discrepancies_summed"
                        or current_section == "cached_glucose_samples"
                        or current_section == "cached_carb_entries"
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

                    elif (
                        not line.startswith("settings")
                        and current_section == Sections.LOOP_DATA_MANAGER
                    ):
                        one = "one"
                    elif(line.startswith("* basalProfileApplyingOverrideHistory")):
                        dict = all_sections[current_section]
                        dict["basalProfileApplyingOverrideHistory"] = line.replace("* basalProfileApplyingOverrideHistory", "")

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
    except Exception as e:
        print("loop report parser error for file : " + dataPathAndName)
        print(e)

    return all_sections





def parse_key_value(all_sections, line):
    dict = all_sections["loop_data_manager"]
    key, value = _split_key_value(line, ":")
    if key or value != "\n":
        if key.startswith("*"):
            key = key[1:]
        if key.startswith(" "):
            key = key[1:]
        if value.endswith("\n"):
            value.replace("\n", "")
        dict[key] = value.replace("\n", "")


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
