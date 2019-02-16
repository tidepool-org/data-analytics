# from projects.parsers.loop_report import LoopReport
import projects.parsers.loop_report as loop_report
import os
import pytest


def test_parse_by_file():
    lr = loop_report.LoopReport()
    loop_dict = lr.parse_by_file(os.getcwd() + "/files", "LoopReport.md")
    assert loop_dict["file_name"] == "LoopReport.md"
    assert loop_dict["loop_version"] == "Loop v1.9.3"
    assert loop_dict["rileyLink_radio_firmware"] == "Optional(subg_rfspy 0.9)"
    assert loop_dict["rileyLink_ble_firmware"] == "Optional(ble_rfspy 0.9)"
    assert loop_dict["carb_ratio_unit"] == "g"
    assert loop_dict["carb_ratio_timeZone"] == -28800

    carb_ratio_schedule = [
        {"startTime": 0.0, "value": 10.0},
        {"startTime": 66600.0, "value": 9.0},
    ]
    assert loop_dict["carb_ratio_schedule"] == carb_ratio_schedule
    assert loop_dict["carb_default_absorption_times_fast"] == 1800.0
    assert loop_dict["carb_default_absorption_times_medium"] == 10800.0
    assert loop_dict["carb_default_absorption_times_slow"] == 18000.0
    insulin_sensitivity_factor_schedule = [
        {"startTime": 0.0, "value": 20.0},
        {"startTime": 9000.0, "value": 40.0},
        {"startTime": 82800.0, "value": 35.0},
    ]
    assert (
        loop_dict["insulin_sensitivity_factor_schedule"]
        == insulin_sensitivity_factor_schedule
    )

    assert loop_dict["insulin_sensitivity_factor_timeZone"] == -28800
    assert loop_dict["insulin_sensitivity_factor_unit"] == "mg/dL"
    assert loop_dict["basal_rate_timeZone"] == -28800
    basal_rate_schedule = [
        {"startTime": 0.0, "value": 0.8},
        {"startTime": 23400.0, "value": 0.8},
        {"startTime": 72000.0, "value": 0.6},
    ]
    assert loop_dict["basal_rate_schedule"] == basal_rate_schedule
    assert loop_dict["insulin_model"] == "humalogNovologAdult"
    assert loop_dict["insulin_action_duration"] == 21600.0
    assert loop_dict["pump_manager_type"] == "minimed"
    assert loop_dict["pump_model"] == "723"
    assert loop_dict["maximum_basal_rate"] == 4.0
    assert loop_dict["maximum_bolus"] == 10.0
    assert loop_dict["retrospective_correction_enabled"] == "true"
    assert loop_dict["suspend_threshold"] == 85.0
    assert loop_dict["suspend_threshold_unit"] == "mg/dL"
    override_range_workout = [135.0, 145.0]
    assert loop_dict["override_range_workout"] == override_range_workout
    override_range_premeal = [70.0, 80.0]
    assert loop_dict["override_range_premeal"] == override_range_premeal
    assert (
        loop_dict["retrospective_glucose_discrepancies_summed"]
        == get_retrospective_glucose_discrepancies_summed()
    )
    assert (
        loop_dict["insulin_counteraction_effects"]
        == get_insulin_counteraction_effects()
    )
    assert loop_dict["get_reservoir_values"] == get_reservoir_values()
    assert loop_dict["predicted_glucose"] == get_predicted_glucose()
    assert (
        loop_dict["retrospective_glucose_discrepancies"]
        == get_retrospective_glucose_discrepancies()
    )
    assert loop_dict["carb_effect"] == get_carb_effect()
    assert loop_dict["insulin_effect"] == get_insulin_effect()
    assert (
        loop_dict["get_normalized_pump_event_dose"] == get_normalized_pump_even_dose()
    )
    assert loop_dict["get_normalized_dose_entries"] == get_normalized_dose_entries()
    assert loop_dict["cached_dose_entries"] == get_cached_dose_entries()
    assert loop_dict["get_pump_event_values"] == get_pump_event_values()
    assert loop_dict["message_log"] == get_message_log()
    assert loop_dict["g5_cgm_manager"] == get_g5_cgm_manager()
    assert loop_dict["dex_cgm_manager"] == {
        "latestBackfill": {
            "glucose": " 98",
            "trend": " 5",
            "timestamp": " 2018-12-13 21",
        }
    }
    assert loop_dict["riley_link_pump_manager"] == {
        "rileyLinkConnectionManager": " Optional(RileyLinkBLEKit.RileyLinkConnectionManager)",
        "lastTimerTick": " 2019-01-28 14:26:19 +0000",
    }
    assert loop_dict["riley_link_device_manager"] == get_riley_link_device_manager()
    assert loop_dict["persistence_controller"] == get_persistence_controller()
    assert loop_dict["glucose_store"] == get_glucose_store()
    assert loop_dict["cached_glucose_samples"] == get_cached_glucose_samples()
    assert loop_dict["cached_carb_entries"] == get_cached_carb_entries()
    assert loop_dict["insulin_delivery_store"] == get_insulin_delivery_store()


def get_pump_event_values():
    return [
        {
            "date": "2019-01-28 15:01:27 +0000",
            "persistedDate": "2019-01-28 15:06:41 +0000",
            "dose": "nil",
            "isUploaded": "false",
            "objectIDURL": "x-coredata://17F97154-93F5-49F8-9870-B15219F6980C/PumpEvent/p50085",
            "raw": "Optional(8 bytes",
            "title": "Optional(TempBasalPumpEvent(length",
            "rawData": "8 bytes",
            "rateType": "MinimedKit.TempBasalPumpEvent.RateType.Absolute",
            "rate": "0.0",
            "timestamp": "calendar",
            "type": "nil",
        },
        {
            "date": "2019-01-28 15:01:27 +0000",
            "persistedDate": "2019-01-28 15:06:41 +0000",
            "dose": "Optional(LoopKit.DoseEntry(type",
            "startDate": "2019-01-28 15:01:27 +0000",
            "endDate": "2019-01-28 15:31:27 +0000",
            "value": "0.0",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": "Optional(16011b41075c13",
            "scheduledBasalRate": "nil",
            "isUploaded": "true",
            "objectIDURL": "x-coredata://17F97154-93F5-49F8-9870-B15219F6980C/PumpEvent/p50084",
            "raw": "Optional(7 bytes",
            "title": "Optional(TempBasalDurationPumpEvent(length",
            "rawData": "7 bytes",
            "duration": "30",
            "timestamp": "calendar",
            "type": "Optional(LoopKit.PumpEventType.tempBasal",
        },
        {
            "date": "2019-01-28 14:51:28 +0000",
            "persistedDate": "2019-01-28 14:56:28 +0000",
            "dose": "nil",
            "isUploaded": "false",
            "objectIDURL": "x-coredata://17F97154-93F5-49F8-9870-B15219F6980C/PumpEvent/p50083",
            "raw": "Optional(8 bytes",
            "title": "Optional(TempBasalPumpEvent(length",
            "rawData": "8 bytes",
            "rateType": "MinimedKit.TempBasalPumpEvent.RateType.Absolute",
            "rate": "0.0",
            "timestamp": "calendar",
            "type": "nil",
        },
        {
            "date": "2019-01-28 14:51:28 +0000",
            "persistedDate": "2019-01-28 14:56:28 +0000",
            "dose": "Optional(LoopKit.DoseEntry(type",
            "startDate": "2019-01-28 14:51:28 +0000",
            "endDate": "2019-01-29 14:51:28 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": "Optional(7b011c73061c130d2000",
            "scheduledBasalRate": "nil",
            "isUploaded": "false",
            "objectIDURL": "x-coredata://17F97154-93F5-49F8-9870-B15219F6980C/PumpEvent/p50082",
            "raw": "Optional(10 bytes",
            "title": "Optional(BasalProfileStartPumpEvent(length",
            "rawData": "10 bytes",
            "timestamp": "calendar",
            "scheduleEntry": "MinimedKit.BasalScheduleEntry(index",
            "timeOffset": "23400.0",
            "rate": "0.8",
            "type": "Optional(LoopKit.PumpEventType.basal",
        },
        {
            "date": "2019-01-28 14:51:28 +0000",
            "persistedDate": "2019-01-28 14:56:28 +0000",
            "dose": "Optional(LoopKit.DoseEntry(type",
            "startDate": "2019-01-28 14:51:28 +0000",
            "endDate": "2019-01-28 14:51:28 +0000",
            "value": "0.0",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": "Optional(16001c73065c13",
            "scheduledBasalRate": "nil",
            "isUploaded": "true",
            "objectIDURL": "x-coredata://17F97154-93F5-49F8-9870-B15219F6980C/PumpEvent/p50081",
            "raw": "Optional(7 bytes",
            "title": "Optional(TempBasalDurationPumpEvent(length",
            "rawData": "7 bytes",
            "duration": "0",
            "timestamp": "calendar",
            "type": "Optional(LoopKit.PumpEventType.tempBasal",
        },
        {
            "date": "2019-01-28 14:46:28 +0000",
            "persistedDate": "2019-01-28 14:51:28 +0000",
            "dose": "nil",
            "isUploaded": "false",
            "objectIDURL": "x-coredata://17F97154-93F5-49F8-9870-B15219F6980C/PumpEvent/p50080",
            "raw": "Optional(8 bytes",
            "title": "Optional(TempBasalPumpEvent(length",
            "rawData": "8 bytes",
            "rateType": "MinimedKit.TempBasalPumpEvent.RateType.Absolute",
            "rate": "0.0",
            "timestamp": "calendar",
            "type": "nil",
        },
        {
            "date": "2019-01-28 14:46:28 +0000",
            "persistedDate": "2019-01-28 14:51:28 +0000",
            "dose": "Optional(LoopKit.DoseEntry(type",
            "startDate": "2019-01-28 14:46:28 +0000",
            "endDate": "2019-01-28 15:16:28 +0000",
            "value": "0.0",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": "Optional(16011c6e065c13",
            "scheduledBasalRate": "nil",
            "isUploaded": "true",
            "objectIDURL": "x-coredata://17F97154-93F5-49F8-9870-B15219F6980C/PumpEvent/p50079",
            "raw": "Optional(7 bytes",
            "title": "Optional(TempBasalDurationPumpEvent(length",
            "rawData": "7 bytes",
            "duration": "30",
            "timestamp": "calendar",
            "type": "Optional(LoopKit.PumpEventType.tempBasal",
        },
        {
            "date": "2019-01-28 14:41:28 +0000",
            "persistedDate": "2019-01-28 14:46:28 +0000",
            "dose": "nil",
            "isUploaded": "false",
            "objectIDURL": "x-coredata://17F97154-93F5-49F8-9870-B15219F6980C/PumpEvent/p50078",
            "raw": "Optional(8 bytes",
            "title": "Optional(TempBasalPumpEvent(length",
            "rawData": "8 bytes",
            "rateType": "MinimedKit.TempBasalPumpEvent.RateType.Absolute",
            "rate": "1.2",
            "timestamp": "calendar",
            "type": "nil",
        },
        {
            "date": "2019-01-28 14:41:28 +0000",
            "persistedDate": "2019-01-28 14:46:28 +0000",
            "dose": "Optional(LoopKit.DoseEntry(type",
            "startDate": "2019-01-28 14:41:28 +0000",
            "endDate": "2019-01-28 15:11:28 +0000",
            "value": "1.2",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": "Optional(16011c69065c13",
            "scheduledBasalRate": "nil",
            "isUploaded": "true",
            "objectIDURL": "x-coredata://17F97154-93F5-49F8-9870-B15219F6980C/PumpEvent/p50077",
            "raw": "Optional(7 bytes",
            "title": "Optional(TempBasalDurationPumpEvent(length",
            "rawData": "7 bytes",
            "duration": "30",
            "timestamp": "calendar",
            "type": "Optional(LoopKit.PumpEventType.tempBasal",
        },
        {
            "date": "2019-01-28 14:36:27 +0000",
            "persistedDate": "2019-01-28 14:41:28 +0000",
            "dose": "nil",
            "isUploaded": "false",
            "objectIDURL": "x-coredata://17F97154-93F5-49F8-9870-B15219F6980C/PumpEvent/p50076",
            "raw": "Optional(8 bytes",
            "title": "Optional(TempBasalPumpEvent(length",
            "rawData": "8 bytes",
            "rateType": "MinimedKit.TempBasalPumpEvent.RateType.Absolute",
            "rate": "1.4",
            "timestamp": "calendar",
            "type": "nil",
        },
        {
            "date": "2019-01-28 14:36:27 +0000",
            "persistedDate": "2019-01-28 14:41:28 +0000",
            "dose": "Optional(LoopKit.DoseEntry(type",
            "startDate": "2019-01-28 14:36:27 +0000",
            "endDate": "2019-01-28 15:06:27 +0000",
            "value": "1.4",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": "Optional(16011b64065c13",
            "scheduledBasalRate": "nil",
            "isUploaded": "true",
            "objectIDURL": "x-coredata://17F97154-93F5-49F8-9870-B15219F6980C/PumpEvent/p50075",
            "raw": "Optional(7 bytes",
            "title": "Optional(TempBasalDurationPumpEvent(length",
            "rawData": "7 bytes",
            "duration": "30",
            "timestamp": "calendar",
            "type": "Optional(LoopKit.PumpEventType.tempBasal",
        },
        {
            "date": "2019-01-28 14:30:00 +0000",
            "persistedDate": "2019-01-28 14:31:28 +0000",
            "dose": "Optional(LoopKit.DoseEntry(type",
            "startDate": "2019-01-28 14:30:00 +0000",
            "endDate": "2019-01-29 14:30:00 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": "Optional(7b01005e061c130d2000",
            "scheduledBasalRate": "nil",
            "isUploaded": "false",
            "objectIDURL": "x-coredata://17F97154-93F5-49F8-9870-B15219F6980C/PumpEvent/p50074",
            "raw": "Optional(10 bytes",
            "title": "Optional(BasalProfileStartPumpEvent(length",
            "rawData": "10 bytes",
            "timestamp": "calendar",
            "scheduleEntry": "MinimedKit.BasalScheduleEntry(index",
            "timeOffset": "23400.0",
            "rate": "0.8",
            "type": "Optional(LoopKit.PumpEventType.basal",
        },
        {
            "date": "2019-01-28 14:06:27 +0000",
            "persistedDate": "2019-01-28 14:11:28 +0000",
            "dose": "Optional(LoopKit.DoseEntry(type",
            "startDate": "2019-01-28 14:06:27 +0000",
            "endDate": "2019-01-29 14:06:27 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": "Optional(7b001b46061c13002000",
            "scheduledBasalRate": "nil",
            "isUploaded": "false",
            "objectIDURL": "x-coredata://17F97154-93F5-49F8-9870-B15219F6980C/PumpEvent/p50071",
            "raw": "Optional(10 bytes",
            "title": "Optional(BasalProfileStartPumpEvent(length",
            "rawData": "10 bytes",
            "timestamp": "calendar",
            "scheduleEntry": "MinimedKit.BasalScheduleEntry(index",
            "timeOffset": "0.0",
            "rate": "0.8",
            "type": "Optional(LoopKit.PumpEventType.basal",
        },
        {
            "date": "2019-01-28 14:06:27 +0000",
            "persistedDate": "2019-01-28 14:11:28 +0000",
            "dose": "Optional(LoopKit.DoseEntry(type",
            "startDate": "2019-01-28 14:06:27 +0000",
            "endDate": "2019-01-28 14:06:27 +0000",
            "value": "0.0",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": "Optional(16001b46065c13",
            "scheduledBasalRate": "nil",
            "isUploaded": "true",
            "objectIDURL": "x-coredata://17F97154-93F5-49F8-9870-B15219F6980C/PumpEvent/p50072",
            "raw": "Optional(7 bytes",
            "title": "Optional(TempBasalDurationPumpEvent(length",
            "rawData": "7 bytes",
            "duration": "0",
            "timestamp": "calendar",
            "type": "Optional(LoopKit.PumpEventType.tempBasal",
        },
        {
            "date": "2019-01-28 14:06:27 +0000",
            "persistedDate": "2019-01-28 14:11:28 +0000",
            "dose": "nil",
            "isUploaded": "false",
            "objectIDURL": "x-coredata://17F97154-93F5-49F8-9870-B15219F6980C/PumpEvent/p50073",
            "raw": "Optional(8 bytes",
            "title": "Optional(TempBasalPumpEvent(length",
            "rawData": "8 bytes",
            "rateType": "MinimedKit.TempBasalPumpEvent.RateType.Absolute",
            "rate": "0.0",
            "timestamp": "calendar",
            "type": "nil",
        },
        {
            "date": "2019-01-28 14:01:41 +0000",
            "persistedDate": "2019-01-28 14:01:58 +0000",
            "dose": "Optional(LoopKit.DoseEntry(type",
            "startDate": "2019-01-28 14:01:41 +0000",
            "endDate": "2019-01-28 14:31:41 +0000",
            "value": "0.0",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": "Optional(16012941065c13",
            "scheduledBasalRate": "nil",
            "isUploaded": "true",
            "objectIDURL": "x-coredata://17F97154-93F5-49F8-9870-B15219F6980C/PumpEvent/p50069",
            "raw": "Optional(7 bytes",
            "title": "Optional(TempBasalDurationPumpEvent(length",
            "rawData": "7 bytes",
            "duration": "30",
            "timestamp": "calendar",
            "type": "Optional(LoopKit.PumpEventType.tempBasal",
        },
        {
            "date": "2019-01-28 14:01:41 +0000",
            "persistedDate": "2019-01-28 14:01:58 +0000",
            "dose": "nil",
            "isUploaded": "false",
            "objectIDURL": "x-coredata://17F97154-93F5-49F8-9870-B15219F6980C/PumpEvent/p50067",
            "raw": "Optional(8 bytes",
            "title": "Optional(TempBasalPumpEvent(length",
            "rawData": "8 bytes",
            "rateType": "MinimedKit.TempBasalPumpEvent.RateType.Absolute",
            "rate": "0.0",
            "timestamp": "calendar",
            "type": "nil",
        },
        {
            "date": "2019-01-28 13:56:27 +0000",
            "persistedDate": "2019-01-28 14:01:58 +0000",
            "dose": "Optional(LoopKit.DoseEntry(type",
            "startDate": "2019-01-28 13:56:27 +0000",
            "endDate": "2019-01-28 14:26:27 +0000",
            "value": "0.375",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": "Optional(16011b78055c13",
            "scheduledBasalRate": "nil",
            "isUploaded": "true",
            "objectIDURL": "x-coredata://17F97154-93F5-49F8-9870-B15219F6980C/PumpEvent/p50070",
            "raw": "Optional(7 bytes",
            "title": "Optional(TempBasalDurationPumpEvent(length",
            "rawData": "7 bytes",
            "duration": "30",
            "timestamp": "calendar",
            "type": "Optional(LoopKit.PumpEventType.tempBasal",
        },
        {
            "date": "2019-01-28 13:56:27 +0000",
            "persistedDate": "2019-01-28 14:01:58 +0000",
            "dose": "nil",
            "isUploaded": "false",
            "objectIDURL": "x-coredata://17F97154-93F5-49F8-9870-B15219F6980C/PumpEvent/p50068",
            "raw": "Optional(8 bytes",
            "title": "Optional(TempBasalPumpEvent(length",
            "rawData": "8 bytes",
            "rateType": "MinimedKit.TempBasalPumpEvent.RateType.Absolute",
            "rate": "0.375",
            "timestamp": "calendar",
            "type": "nil",
        },
    ]


def test_parse_by_directory():
    lr = loop_report.LoopReport()
    list_of_files = lr.parse_by_directory(os.path.realpath("files"))
    assert len(list_of_files) == 2


def test_parse_by_file_missing_file_name():
    with pytest.raises(RuntimeError) as excinfo:
        lr = loop_report.LoopReport()
        lr.parse_by_file(os.getcwd() + "/files", "")
    assert "The file path or file name passed in is invalid." in str(excinfo.value)


def test_parse_by_file_invalid_directory():
    with pytest.raises(RuntimeError) as excinfo:
        lr = loop_report.LoopReport()
        lr.parse_by_file("", "test_loop_report.py")
    assert "The file path or file name passed in is invalid." in str(excinfo.value)


def test_parse_by_directory_invalid_directory():
    with pytest.raises(RuntimeError) as excinfo:
        lr = loop_report.LoopReport()
        lr.parse_by_directory("")
    assert "The directory passed in is invalid." in str(excinfo.value)


def get_insulin_counteraction_effects():
    return [
        {
            "start_time": "2019-01-27 15:16:22 +0000",
            "end_time": " 2019-01-27 15:21:22 +0000",
            "value": " 0.12323223579096947",
            "units": "mg/dL/min",
        },
        {
            "start_time": "2019-01-27 15:21:22 +0000",
            "end_time": " 2019-01-27 15:26:22 +0000",
            "value": " 0.11340556858587406",
            "units": "mg/dL/min",
        },
        {
            "start_time": "2019-01-27 15:26:22 +0000",
            "end_time": " 2019-01-27 15:31:22 +0000",
            "value": " -0.09644491407321425",
            "units": "mg/dL/min",
        },
        {
            "start_time": "2019-01-27 15:31:22 +0000",
            "end_time": " 2019-01-27 15:36:22 +0000",
            "value": " -0.5038144363643894",
            "units": "mg/dL/min",
        },
        {
            "start_time": "2019-01-27 15:36:22 +0000",
            "end_time": " 2019-01-27 15:41:22 +0000",
            "value": " 0.09110549888380319",
            "units": "mg/dL/min",
        },
        {
            "start_time": "2019-01-27 15:41:22 +0000",
            "end_time": " 2019-01-27 15:46:22 +0000",
            "value": " 0.08806492424520086",
            "units": "mg/dL/min",
        },
        {
            "start_time": "2019-01-27 15:46:22 +0000",
            "end_time": " 2019-01-27 15:51:21 +0000",
            "value": " 0.2877941626511216",
            "units": "mg/dL/min",
        },
        {
            "start_time": "2019-01-27 15:51:21 +0000",
            "end_time": " 2019-01-27 15:56:22 +0000",
            "value": " -0.11365967464421017",
            "units": "mg/dL/min",
        },
        {
            "start_time": "2019-01-27 15:56:22 +0000",
            "end_time": " 2019-01-27 16:01:22 +0000",
            "value": " -0.3170549421296755",
            "units": "mg/dL/min",
        },
        {
            "start_time": "2019-01-27 16:01:22 +0000",
            "end_time": " 2019-01-27 16:06:22 +0000",
            "value": " -0.12201958445077564",
            "units": "mg/dL/min",
        },
        {
            "start_time": "2019-01-27 16:06:22 +0000",
            "end_time": " 2019-01-27 16:11:22 +0000",
            "value": " -0.1286808487354534",
            "units": "mg/dL/min",
        },
        {
            "start_time": "2019-01-27 16:11:22 +0000",
            "end_time": " 2019-01-27 16:16:22 +0000",
            "value": " -0.5368095386319524",
            "units": "mg/dL/min",
        },
        {
            "start_time": "2019-01-27 16:16:22 +0000",
            "end_time": " 2019-01-27 16:21:22 +0000",
            "value": " -0.9461971753678154",
            "units": "mg/dL/min",
        },
        {
            "start_time": "2019-01-27 16:21:22 +0000",
            "end_time": " 2019-01-27 16:26:22 +0000",
            "value": " -0.9566544114980243",
            "units": "mg/dL/min",
        },
        {
            "start_time": "2019-01-27 16:26:22 +0000",
            "end_time": " 2019-01-27 16:31:22 +0000",
            "value": " -0.1680095551964925",
            "units": "mg/dL/min",
        },
    ]


def get_retrospective_glucose_discrepancies_summed():
    return [
        {
            "start_time": "2018-11-28 00:02:31 +0000",
            "end_time": " 2018-11-28 00:02:31 +0000",
            "value": " 13.150577197081377",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 00:02:31 +0000",
            "end_time": " 2018-11-28 00:07:31 +0000",
            "value": " 26.06978171944507",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 00:02:31 +0000",
            "end_time": " 2018-11-28 00:12:31 +0000",
            "value": " 38.67818952118729",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 00:02:31 +0000",
            "end_time": " 2018-11-28 00:17:31 +0000",
            "value": " 49.22323442360305",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 00:02:31 +0000",
            "end_time": " 2018-11-28 00:22:31 +0000",
            "value": " 57.644897625857766",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 00:02:31 +0000",
            "end_time": " 2018-11-28 00:27:31 +0000",
            "value": " 64.15869871324333",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 00:02:31 +0000",
            "end_time": " 2018-11-28 00:32:31 +0000",
            "value": " 67.1655997352358",
            "units": "mg/dL",
        },
    ]


def get_insulin_counteration_effects():
    return [
        {
            "start_time": "2019-01-27 15:16:22 +0000",
            "end_time": " 2019-01-27 15:21:22 +0000",
            "value": " 0.12323223579096947",
            "units": "mg/dL/min",
        },
        {
            "start_time": "2019-01-27 15:21:22 +0000",
            "end_time": " 2019-01-27 15:26:22 +0000",
            "value": " 0.11340556858587406",
            "units": "mg/dL/min",
        },
        {
            "start_time": "2019-01-27 15:26:22 +0000",
            "end_time": " 2019-01-27 15:31:22 +0000",
            "value": " -0.09644491407321425",
            "units": "mg/dL/min",
        },
        {
            "start_time": "2019-01-27 15:31:22 +0000",
            "end_time": " 2019-01-27 15:36:22 +0000",
            "value": " -0.5038144363643894",
            "units": "mg/dL/min",
        },
        {
            "start_time": "2019-01-27 15:36:22 +0000",
            "end_time": " 2019-01-27 15:41:22 +0000",
            "value": " 0.09110549888380319",
            "units": "mg/dL/min",
        },
        {
            "start_time": "2019-01-27 15:41:22 +0000",
            "end_time": " 2019-01-27 15:46:22 +0000",
            "value": " 0.08806492424520086",
            "units": "mg/dL/min",
        },
        {
            "start_time": "2019-01-27 15:46:22 +0000",
            "end_time": " 2019-01-27 15:51:21 +0000",
            "value": " 0.2877941626511216",
            "units": "mg/dL/min",
        },
        {
            "start_time": "2019-01-27 15:51:21 +0000",
            "end_time": " 2019-01-27 15:56:22 +0000",
            "value": " -0.11365967464421017",
            "units": "mg/dL/min",
        },
        {
            "start_time": "2019-01-27 15:56:22 +0000",
            "end_time": " 2019-01-27 16:01:22 +0000",
            "value": " -0.3170549421296755",
            "units": "mg/dL/min",
        },
        {
            "start_time": "2019-01-27 16:01:22 +0000",
            "end_time": " 2019-01-27 16:06:22 +0000",
            "value": " -0.12201958445077564",
            "units": "mg/dL/min",
        },
        {
            "start_time": "2019-01-27 16:06:22 +0000",
            "end_time": " 2019-01-27 16:11:22 +0000",
            "value": " -0.1286808487354534",
            "units": "mg/dL/min",
        },
        {
            "start_time": "2019-01-27 16:11:22 +0000",
            "end_time": " 2019-01-27 16:16:22 +0000",
            "value": " -0.5368095386319524",
            "units": "mg/dL/min",
        },
        {
            "start_time": "2019-01-27 16:16:22 +0000",
            "end_time": " 2019-01-27 16:21:22 +0000",
            "value": " -0.9461971753678154",
            "units": "mg/dL/min",
        },
        {
            "start_time": "2019-01-27 16:21:22 +0000",
            "end_time": " 2019-01-27 16:26:22 +0000",
            "value": " -0.9566544114980243",
            "units": "mg/dL/min",
        },
        {
            "start_time": "2019-01-27 16:26:22 +0000",
            "end_time": " 2019-01-27 16:31:22 +0000",
            "value": " -0.1680095551964925",
            "units": "mg/dL/min",
        },
    ]


def get_message_log():
    return [
        "2019-01-08 18:42:00 +0000 send 1f0d624118030e01008179",
        "2019-01-08 18:42:02 +0000 receive 1f0d62411c0a1d2803c0a000003d9bff81b4",
        "2019-01-08 18:46:07 +0000 send 1f0d624120030e010002cd",
        "2019-01-08 18:46:09 +0000 receive 1f0d6241240a1d2803c1a000003dabff0342",
        "2019-01-08 18:46:11 +0000 send 1f0d624128071f054c4d1dbb0280ff",
        "2019-01-08 18:46:14 +0000 receive 1f0d62412c0a1d1803c1d000003dabff82a6",
    ]


def get_cached_dose_entries():
    return [
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-07 20:43:18 +0000",
            "endDate": "2019-01-07 20:43:21 +0000",
            "value": "0.0",
            "unit": "LoopKit.DoseUnit.units",
            "description": "nil",
            "syncIdentifier": 'Optional("BasalRateSchedule 2019-01-07T20:43:18Z 2019-01-07T20:43:21Z"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.tempBasal",
            "startDate": "2019-01-07 20:43:21 +0000",
            "endDate": "2019-01-07 21:13:21 +0000",
            "value": "0.95",
            "unit": "LoopKit.DoseUnit.units",
            "description": "nil",
            "syncIdentifier": 'Optional("74656d70426173616c20302e39323520323031392d30312d30375432303a34333a32315a20313830302e30"',
            "scheduledBasalRate": "Optional(0.9 IU/hr",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-07 21:13:21 +0000",
            "endDate": "2019-01-07 21:16:57 +0000",
            "value": "0.05",
            "unit": "LoopKit.DoseUnit.units",
            "description": "nil",
            "syncIdentifier": 'Optional("BasalRateSchedule 2019-01-07T21:13:21Z 2019-01-07T21:16:57Z"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.tempBasal",
            "startDate": "2019-01-07 21:16:57 +0000",
            "endDate": "2019-01-07 21:21:14 +0000",
            "value": "0.0",
            "unit": "LoopKit.DoseUnit.units",
            "description": "nil",
            "syncIdentifier": 'Optional("74656d70426173616c20302e3020323031392d30312d30375432313a31363a35375a203235372e3132383533333935393338383733"',
            "scheduledBasalRate": "Optional(0.9 IU/hr",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-07 21:21:14 +0000",
            "endDate": "2019-01-07 21:21:20 +0000",
            "value": "0.0",
            "unit": "LoopKit.DoseUnit.units",
            "description": "nil",
            "syncIdentifier": 'Optional("BasalRateSchedule 2019-01-07T21:21:14Z 2019-01-07T21:21:20Z"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.tempBasal",
            "startDate": "2019-01-07 21:21:20 +0000",
            "endDate": "2019-01-07 21:26:00 +0000",
            "value": "0.0",
            "unit": "LoopKit.DoseUnit.units",
            "description": "nil",
            "syncIdentifier": 'Optional("74656d70426173616c20302e3020323031392d30312d30375432313a32313a32305a203237392e37333436363930383933313733"',
            "scheduledBasalRate": "Optional(0.9 IU/hr",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-07 21:26:00 +0000",
            "endDate": "2019-01-07 21:26:08 +0000",
            "value": "0.0",
            "unit": "LoopKit.DoseUnit.units",
            "description": "nil",
            "syncIdentifier": 'Optional("BasalRateSchedule 2019-01-07T21:26:00Z 2019-01-07T21:26:08Z"',
            "scheduledBasalRate": "nil",
        },
    ]


def get_normalized_dose_entries():
    return [
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-24 14:11:24 +0000",
            "endDate": "2019-01-24 14:13:17 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b00004b061813002000"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.suspend",
            "startDate": "2019-01-24 14:13:17 +0000",
            "endDate": "2019-01-24 14:13:58 +0000",
            "value": "0.0",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("2100354c061813"',
            "scheduledBasalRate": "Optional(0.8 IU/hr",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-24 14:13:58 +0000",
            "endDate": "2019-01-24 14:14:28 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("030000002f224d261813"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-24 14:14:28 +0000",
            "endDate": "2019-01-24 14:30:24 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b00044e061813002000"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-24 14:30:24 +0000",
            "endDate": "2019-01-24 14:53:31 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b01005e0618130d2000"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-24 14:53:31 +0000",
            "endDate": "2019-01-24 15:31:25 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b0107750658130d2000"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-24 15:31:25 +0000",
            "endDate": "2019-01-24 17:36:24 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b01195f0718130d2000"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-24 17:36:24 +0000",
            "endDate": "2019-01-24 20:06:25 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b0118640918130d2000"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-24 20:06:25 +0000",
            "endDate": "2019-01-24 20:36:24 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b0119460c18130d2000"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-24 20:36:24 +0000",
            "endDate": "2019-01-24 21:36:25 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b0118640c18130d2000"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-24 21:36:25 +0000",
            "endDate": "2019-01-24 22:06:24 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b0119640d18130d2000"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-24 22:06:24 +0000",
            "endDate": "2019-01-25 01:06:25 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b0118460e18130d2000"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-25 01:06:25 +0000",
            "endDate": "2019-01-25 01:31:27 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b0119461118130d2000"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-25 01:31:27 +0000",
            "endDate": "2019-01-25 02:36:24 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b011b5f1118130d2000"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-25 02:36:24 +0000",
            "endDate": "2019-01-25 03:11:24 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b0118641218130d2000"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-25 03:11:24 +0000",
            "endDate": "2019-01-25 04:51:24 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b01184b1318130d2000"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-25 04:51:24 +0000",
            "endDate": "2019-01-25 05:01:25 +0000",
            "value": "0.6",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b021873141813281800"',
            "scheduledBasalRate": "nil",
        },
    ]


def get_normalized_pump_even_dose():
    return [
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-24 14:11:24 +0000",
            "endDate": "2019-01-24 14:13:17 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b00004b061813002000"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.suspend",
            "startDate": "2019-01-24 14:13:17 +0000",
            "endDate": "2019-01-24 14:13:58 +0000",
            "value": "0.0",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("2100354c061813"',
            "scheduledBasalRate": "Optional(0.8 IU/hr",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-24 14:13:58 +0000",
            "endDate": "2019-01-24 14:14:28 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("030000002f224d261813"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-24 14:14:28 +0000",
            "endDate": "2019-01-24 14:30:24 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b00044e061813002000"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-24 14:30:24 +0000",
            "endDate": "2019-01-24 14:53:31 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b01005e0618130d2000"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-24 14:53:31 +0000",
            "endDate": "2019-01-24 15:31:25 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b0107750658130d2000"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-24 15:31:25 +0000",
            "endDate": "2019-01-24 17:36:24 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b01195f0718130d2000"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-24 17:36:24 +0000",
            "endDate": "2019-01-24 20:06:25 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b0118640918130d2000"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-24 20:06:25 +0000",
            "endDate": "2019-01-24 20:36:24 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b0119460c18130d2000"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-24 20:36:24 +0000",
            "endDate": "2019-01-24 21:36:25 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b0118640c18130d2000"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-25 17:26:28 +0000",
            "endDate": "2019-01-25 18:36:45 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b011c5a0919130d2000"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-25 18:36:45 +0000",
            "endDate": "2019-01-25 19:16:28 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b012d640a19130d2000"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-27 14:21:28 +0000",
            "endDate": "2019-01-27 14:41:27 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b001c55061b13002000"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-27 14:41:27 +0000",
            "endDate": "2019-01-27 15:21:29 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b011b69061b130d2000"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.tempBasal",
            "startDate": "2019-01-27 15:21:29 +0000",
            "endDate": "2019-01-27 15:22:13 +0000",
            "value": "0.0",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("16011d55075b13"',
            "scheduledBasalRate": "Optional(0.8 IU/hr",
        },
        {
            "type": "LoopKit.DoseType.tempBasal",
            "startDate": "2019-01-27 15:22:13 +0000",
            "endDate": "2019-01-27 15:22:15 +0000",
            "value": "1.625",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("16010d56075b13"',
            "scheduledBasalRate": "Optional(0.8 IU/hr",
        },
        {
            "type": "LoopKit.DoseType.tempBasal",
            "startDate": "2019-01-27 15:22:15 +0000",
            "endDate": "2019-01-27 15:31:27 +0000",
            "value": "1.625",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("16010f56075b13"',
            "scheduledBasalRate": "Optional(0.8 IU/hr",
        },
        {
            "type": "LoopKit.DoseType.tempBasal",
            "startDate": "2019-01-27 15:31:27 +0000",
            "endDate": "2019-01-27 15:36:28 +0000",
            "value": "1.575",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("16011b5f075b13"',
            "scheduledBasalRate": "Optional(0.8 IU/hr",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-27 15:36:28 +0000",
            "endDate": "2019-01-27 15:41:28 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b011c64071b130d2000"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.tempBasal",
            "startDate": "2019-01-27 15:41:28 +0000",
            "endDate": "2019-01-27 15:51:27 +0000",
            "value": "0.0",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("16011c69075b13"',
            "scheduledBasalRate": "Optional(0.8 IU/hr",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-27 15:51:27 +0000",
            "endDate": "2019-01-27 15:56:28 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b011b73071b130d2000"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.tempBasal",
            "startDate": "2019-01-27 15:56:28 +0000",
            "endDate": "2019-01-27 16:17:00 +0000",
            "value": "0.0",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("16011c78075b13"',
            "scheduledBasalRate": "Optional(0.8 IU/hr",
        },
        {
            "type": "LoopKit.DoseType.tempBasal",
            "startDate": "2019-01-27 16:17:00 +0000",
            "endDate": "2019-01-27 16:21:29 +0000",
            "value": "0.0",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("16010051085b13"',
            "scheduledBasalRate": "Optional(0.8 IU/hr",
        },
        {
            "type": "LoopKit.DoseType.tempBasal",
            "startDate": "2019-01-27 16:21:29 +0000",
            "endDate": "2019-01-27 16:41:27 +0000",
            "value": "0.0",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("16011d55085b13"',
            "scheduledBasalRate": "Optional(0.8 IU/hr",
        },
        {
            "type": "LoopKit.DoseType.tempBasal",
            "startDate": "2019-01-27 16:41:27 +0000",
            "endDate": "2019-01-27 16:46:28 +0000",
            "value": "0.0",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("16011b69085b13"',
            "scheduledBasalRate": "Optional(0.8 IU/hr",
        },
        {
            "type": "LoopKit.DoseType.tempBasal",
            "startDate": "2019-01-27 16:46:28 +0000",
            "endDate": "2019-01-27 16:51:27 +0000",
            "value": "2.825",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("16011c6e085b13"',
            "scheduledBasalRate": "Optional(0.8 IU/hr",
        },
        {
            "type": "LoopKit.DoseType.tempBasal",
            "startDate": "2019-01-27 16:51:27 +0000",
            "endDate": "2019-01-27 16:56:28 +0000",
            "value": "2.975",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("16011b73085b13"',
            "scheduledBasalRate": "Optional(0.8 IU/hr",
        },
        {
            "type": "LoopKit.DoseType.tempBasal",
            "startDate": "2019-01-27 16:56:28 +0000",
            "endDate": "2019-01-27 17:01:27 +0000",
            "value": "1.85",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("16011c78085b13"',
            "scheduledBasalRate": "Optional(0.8 IU/hr",
        },
        {
            "type": "LoopKit.DoseType.tempBasal",
            "startDate": "2019-01-27 17:01:27 +0000",
            "endDate": "2019-01-27 17:06:27 +0000",
            "value": "1.425",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("16011b41095b13"',
            "scheduledBasalRate": "Optional(0.8 IU/hr",
        },
        {
            "type": "LoopKit.DoseType.tempBasal",
            "startDate": "2019-01-27 17:06:27 +0000",
            "endDate": "2019-01-27 17:11:41 +0000",
            "value": "1.15",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("16011b46095b13"',
            "scheduledBasalRate": "Optional(0.8 IU/hr",
        },
        {
            "type": "LoopKit.DoseType.tempBasal",
            "startDate": "2019-01-27 17:11:41 +0000",
            "endDate": "2019-01-27 17:31:31 +0000",
            "value": "1.275",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("1601294b095b13"',
            "scheduledBasalRate": "Optional(0.8 IU/hr",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-27 17:31:32 +0000",
            "endDate": "2019-01-27 17:36:28 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b01205f091b130d2000"',
            "scheduledBasalRate": "nil",
        },
        {
            "type": "LoopKit.DoseType.tempBasal",
            "startDate": "2019-01-27 17:36:28 +0000",
            "endDate": "2019-01-27 17:41:28 +0000",
            "value": "0.525",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("16011c64095b13"',
            "scheduledBasalRate": "Optional(0.8 IU/hr",
        },
        {
            "type": "LoopKit.DoseType.tempBasal",
            "startDate": "2019-01-27 17:41:28 +0000",
            "endDate": "2019-01-27 17:56:42 +0000",
            "value": "1.5",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("16011c69095b13"',
            "scheduledBasalRate": "Optional(0.8 IU/hr",
        },
        {
            "type": "LoopKit.DoseType.tempBasal",
            "startDate": "2019-01-27 17:56:42 +0000",
            "endDate": "2019-01-27 18:26:42 +0000",
            "value": "2.225",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("16012a78095b13"',
            "scheduledBasalRate": "Optional(0.8 IU/hr",
        },
        {
            "type": "LoopKit.DoseType.basal",
            "startDate": "2019-01-27 18:26:42 +0000",
            "endDate": "2019-01-27 18:30:37 +0000",
            "value": "0.8",
            "unit": "LoopKit.DoseUnit.unitsPerHour",
            "description": "nil",
            "syncIdentifier": 'Optional("7b012a5a0a1b130d2000"',
            "scheduledBasalRate": "nil",
        },
    ]


def get_insulin_effect():
    return [
        {
            "start_time": "2018-11-28 00:30:00 +0000",
            "value": " -598.4414718881781",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 00:35:00 +0000",
            "value": " -608.2232418870775",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 00:40:00 +0000",
            "value": " -618.1781269950548",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 00:45:00 +0000",
            "value": " -628.2362250846572",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 00:50:00 +0000",
            "value": " -638.3355211023576",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 00:55:00 +0000",
            "value": " -648.4211533199497",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 01:00:00 +0000",
            "value": " -658.4447024193285",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 01:05:00 +0000",
            "value": " -668.3632968575748",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 01:10:00 +0000",
            "value": " -678.1394998374639",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 01:15:00 +0000",
            "value": " -687.740877675081",
            "units": "mg/dL",
        },
    ]


def get_carb_effect():
    return [
        {
            "start_time": "2018-11-28 00:00:00 +0000",
            "value": " 309.375",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 00:05:00 +0000",
            "value": " 309.375",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 00:10:00 +0000",
            "value": " 309.375",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 00:15:00 +0000",
            "value": " 309.375",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 00:20:00 +0000",
            "value": " 309.375",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 00:25:00 +0000",
            "value": " 309.375",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 00:30:00 +0000",
            "value": " 309.375",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 00:35:00 +0000",
            "value": " 313.1571581860383",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 00:40:00 +0000",
            "value": " 320.79604707492723",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 00:45:00 +0000",
            "value": " 328.4349359638161",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 00:50:00 +0000",
            "value": " 336.073824852705",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 00:55:00 +0000",
            "value": " 343.7127137415939",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 01:00:00 +0000",
            "value": " 351.3516026304828",
            "units": "mg/dL",
        },
    ]


def get_retrospective_glucose_discrepancies():
    return [
        {
            "start_time": "2018-11-28 00:02:31 +0000",
            "value": " 13.150577197081377",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 00:07:31 +0000",
            "value": " 12.919204522363694",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 00:12:31 +0000",
            "value": " 12.608407801742223",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 00:17:31 +0000",
            "value": " 10.545044902415762",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 00:22:31 +0000",
            "value": " 8.421663202254713",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 00:27:31 +0000",
            "value": " 6.513801087385557",
            "units": "mg/dL",
        },
        {
            "start_time": "2018-11-28 00:32:31 +0000",
            "value": " 3.0069010219924754",
            "units": "mg/dL",
        },
    ]


def get_predicted_glucose():
    return [
        {"start_time": "2019-01-28 15:16:20 +0000", "value": " 85.0", "units": "mg/dL"},
        {
            "start_time": "2019-01-28 15:20:00 +0000",
            "value": " 85.732078872579",
            "units": "mg/dL",
        },
        {
            "start_time": "2019-01-28 15:25:00 +0000",
            "value": " 86.44096256310476",
            "units": "mg/dL",
        },
        {
            "start_time": "2019-01-28 15:30:00 +0000",
            "value": " 86.77019751074303",
            "units": "mg/dL",
        },
        {
            "start_time": "2019-01-28 15:35:00 +0000",
            "value": " 86.74103998552496",
            "units": "mg/dL",
        },
        {
            "start_time": "2019-01-28 15:40:00 +0000",
            "value": " 86.64342159003903",
            "units": "mg/dL",
        },
        {
            "start_time": "2019-01-28 15:45:00 +0000",
            "value": " 86.57898055151605",
            "units": "mg/dL",
        },
        {
            "start_time": "2019-01-28 15:50:00 +0000",
            "value": " 86.54829897295224",
            "units": "mg/dL",
        },
        {
            "start_time": "2019-01-28 15:55:00 +0000",
            "value": " 86.5520006409324",
            "units": "mg/dL",
        },
        {
            "start_time": "2019-01-28 16:00:00 +0000",
            "value": " 86.59083783299144",
            "units": "mg/dL",
        },
        {
            "start_time": "2019-01-28 16:05:00 +0000",
            "value": " 86.66555585381998",
            "units": "mg/dL",
        },
        {
            "start_time": "2019-01-28 16:10:00 +0000",
            "value": " 86.77683520191353",
            "units": "mg/dL",
        },
    ]


def get_reservoir_values():
    return [
        {
            "start_time": "2019-01-28 15:16:00 +0000",
            "value": " 168.9",
            "units": "unitVolume",
        },
        {
            "start_time": "2019-01-28 15:11:00 +0000",
            "value": " 168.9",
            "units": "unitVolume",
        },
        {
            "start_time": "2019-01-28 15:06:00 +0000",
            "value": " 168.9",
            "units": "unitVolume",
        },
        {
            "start_time": "2019-01-28 15:01:00 +0000",
            "value": " 168.9",
            "units": "unitVolume",
        },
        {
            "start_time": "2019-01-28 14:56:00 +0000",
            "value": " 169.0",
            "units": "unitVolume",
        },
        {
            "start_time": "2019-01-28 14:51:00 +0000",
            "value": " 169.1",
            "units": "unitVolume",
        },
        {
            "start_time": "2019-01-28 14:46:00 +0000",
            "value": " 169.1",
            "units": "unitVolume",
        },
        {
            "start_time": "2019-01-28 14:41:00 +0000",
            "value": " 169.2",
            "units": "unitVolume",
        },
        {
            "start_time": "2019-01-28 14:36:00 +0000",
            "value": " 169.3",
            "units": "unitVolume",
        },
        {
            "start_time": "2019-01-28 14:31:00 +0000",
            "value": " 169.3",
            "units": "unitVolume",
        },
        {
            "start_time": "2019-01-28 14:26:00 +0000",
            "value": " 169.4",
            "units": "unitVolume",
        },
        {
            "start_time": "2019-01-28 14:21:00 +0000",
            "value": " 169.5",
            "units": "unitVolume",
        },
        {
            "start_time": "2019-01-28 14:16:00 +0000",
            "value": " 169.5",
            "units": "unitVolume",
        },
    ]


def get_cached_carb_entries():
    return [
        {
            "sampleUUID": " 29A45677-9670-48A0-A6C6-379CEA88581F",
            "syncIdentifier": " 8A570A49-59FF-435B-BEEF-F6BBA0BCDEAA",
            "syncVersion": " 1",
            "startDate": " 2019-01-27 22:02:29 +0000",
            "quantity": " 10 g",
            "foodType": " ",
            "absorptionTime": " 10800.0",
            "createdByCurrentApp": " true",
            "externalID": " 5c4e2a77d8dfb37103e14f78",
            "isUploaded": " true",
        },
        {
            "sampleUUID": " CB1F6944-A6FF-4917-B5F6-7509E8CD9EB8",
            "syncIdentifier": " 8E9EC8B3-7A44-4AB4-A81B-4A54F2AAA18D",
            "syncVersion": " 1",
            "startDate": " 2019-01-28 01:00:59 +0000",
            "quantity": " 25 g",
            "foodType": " ",
            "absorptionTime": " 10800.0",
            "createdByCurrentApp": " true",
            "externalID": " 5c4e4b6bd8dfb37103e1e137",
            "isUploaded": " true",
        },
        {
            "sampleUUID": " 2C030171-3604-4542-B492-9990AF375546",
            "syncIdentifier": " 7FF9C039-BE6E-4479-BE4C-3F7EAC1ECF34",
            "syncVersion": " 1",
            "startDate": " 2019-01-28 05:41:22 +0000",
            "quantity": " 7 g",
            "foodType": " ",
            "absorptionTime": " 10800.0",
            "createdByCurrentApp": " true",
            "externalID": " 5c4e9604d8dfb37103e428d1",
            "isUploaded": " true",
        },
    ]


def get_insulin_delivery_store():
    return {
        "observerQuery": " Optional(<HKObserverQuery:0x2838f1180 active>)",
        "observationStart": " 2019-01-28 04:20:09 +0000",
        "observationEnabled": " true",
        "authorizationRequired": " false",
        "lastBasalEndDate": " 2019-01-28 10:06:28 +0000",
    }


def get_cached_glucose_samples():
    return [
        {
            "sampleUUID": "1A5FEA27-285C-4BB2-87BF-1F3DAC3CA6EB",
            "syncIdentifier": '"1A5FEA27-285C-4BB2-87BF-1F3DAC3CA6EB"',
            "syncVersion": "1",
            "startDate": "2019-01-27 15:21:22 +0000",
            "quantity": "92 mg/dL",
            "isDisplayOnly": "false",
            "provenanceIdentifier": '"com.dexcom.G6"',
        },
        {
            "sampleUUID": "85AC7720-6C3F-4125-AB1D-5ADE22707CD1",
            "syncIdentifier": '"85AC7720-6C3F-4125-AB1D-5ADE22707CD1"',
            "syncVersion": "1",
            "startDate": "2019-01-27 15:26:22 +0000",
            "quantity": "92 mg/dL",
            "isDisplayOnly": "false",
            "provenanceIdentifier": '"com.dexcom.G6"',
        },
        {
            "sampleUUID": "89DE2881-D0F9-436B-836C-B19D450DAD8D",
            "syncIdentifier": '"89DE2881-D0F9-436B-836C-B19D450DAD8D"',
            "syncVersion": "1",
            "startDate": "2019-01-27 15:31:22 +0000",
            "quantity": "91 mg/dL",
            "isDisplayOnly": "false",
            "provenanceIdentifier": '"com.dexcom.G6"',
        },
        {
            "sampleUUID": "BE900B25-BDAC-4FFD-9FC6-D2F1855C6AA4",
            "syncIdentifier": '"BE900B25-BDAC-4FFD-9FC6-D2F1855C6AA4"',
            "syncVersion": "1",
            "startDate": "2019-01-27 15:36:22 +0000",
            "quantity": "88 mg/dL",
            "isDisplayOnly": "false",
            "provenanceIdentifier": '"com.dexcom.G6"',
        },
        {
            "sampleUUID": "12B89D59-60E6-4251-AC57-EA65A7313C9C",
            "syncIdentifier": '"12B89D59-60E6-4251-AC57-EA65A7313C9C"',
            "syncVersion": "1",
            "startDate": "2019-01-27 15:41:22 +0000",
            "quantity": "88 mg/dL",
            "isDisplayOnly": "false",
            "provenanceIdentifier": '"com.dexcom.G6"',
        },
        {
            "sampleUUID": "3172335D-761C-4B62-8288-45F58A19C89A",
            "syncIdentifier": '"3172335D-761C-4B62-8288-45F58A19C89A"',
            "syncVersion": "1",
            "startDate": "2019-01-27 15:46:22 +0000",
            "quantity": "88 mg/dL",
            "isDisplayOnly": "false",
            "provenanceIdentifier": '"com.dexcom.G6"',
        },
        {
            "sampleUUID": "D0861787-FE69-48C0-BED6-25BE432ED62E",
            "syncIdentifier": '"D0861787-FE69-48C0-BED6-25BE432ED62E"',
            "syncVersion": "1",
            "startDate": "2019-01-27 15:51:21 +0000",
            "quantity": "89 mg/dL",
            "isDisplayOnly": "false",
            "provenanceIdentifier": '"com.dexcom.G6"',
        },
        {
            "sampleUUID": "A122F1AB-910C-4A6E-8A6F-0AD1D6F7B274",
            "syncIdentifier": '"A122F1AB-910C-4A6E-8A6F-0AD1D6F7B274"',
            "syncVersion": "1",
            "startDate": "2019-01-27 15:56:22 +0000",
            "quantity": "88 mg/dL",
            "isDisplayOnly": "false",
            "provenanceIdentifier": '"com.dexcom.G6"',
        },
        {
            "sampleUUID": "97CA822A-3E61-4217-A8BA-1D3C7E1C5620",
            "syncIdentifier": '"97CA822A-3E61-4217-A8BA-1D3C7E1C5620"',
            "syncVersion": "1",
            "startDate": "2019-01-27 16:01:22 +0000",
            "quantity": "86 mg/dL",
            "isDisplayOnly": "false",
            "provenanceIdentifier": '"com.dexcom.G6"',
        },
        {
            "sampleUUID": "C94C3098-A946-4155-89E5-A11EAEEDD9B3",
            "syncIdentifier": '"C94C3098-A946-4155-89E5-A11EAEEDD9B3"',
            "syncVersion": "1",
            "startDate": "2019-01-27 16:06:22 +0000",
            "quantity": "85 mg/dL",
            "isDisplayOnly": "false",
            "provenanceIdentifier": '"com.dexcom.G6"',
        },
        {
            "sampleUUID": "407921B2-F4AA-449E-B37B-2740ABB2464A",
            "syncIdentifier": '"407921B2-F4AA-449E-B37B-2740ABB2464A"',
            "syncVersion": "1",
            "startDate": "2019-01-27 16:11:22 +0000",
            "quantity": "84 mg/dL",
            "isDisplayOnly": "false",
            "provenanceIdentifier": '"com.dexcom.G6"',
        },
        {
            "sampleUUID": "FBEE49E9-6EF7-4298-92C5-B8F87BCA1233",
            "syncIdentifier": '"FBEE49E9-6EF7-4298-92C5-B8F87BCA1233"',
            "syncVersion": "1",
            "startDate": "2019-01-27 16:16:22 +0000",
            "quantity": "81 mg/dL",
            "isDisplayOnly": "false",
            "provenanceIdentifier": '"com.dexcom.G6"',
        },
        {
            "sampleUUID": "574F9FD3-E283-4880-9A4D-002B5641E526",
            "syncIdentifier": '"574F9FD3-E283-4880-9A4D-002B5641E526"',
            "syncVersion": "1",
            "startDate": "2019-01-27 16:21:22 +0000",
            "quantity": "76 mg/dL",
            "isDisplayOnly": "false",
            "provenanceIdentifier": '"com.dexcom.G6"',
        },
        {
            "sampleUUID": "960009BD-5B7C-458B-9426-8DEE05DE874D",
            "syncIdentifier": '"960009BD-5B7C-458B-9426-8DEE05DE874D"',
            "syncVersion": "1",
            "startDate": "2019-01-27 16:26:22 +0000",
            "quantity": "71 mg/dL",
            "isDisplayOnly": "false",
            "provenanceIdentifier": '"com.dexcom.G6"',
        },
        {
            "sampleUUID": "C067386B-AB07-42C6-9480-4EF450661287",
            "syncIdentifier": '"C067386B-AB07-42C6-9480-4EF450661287"',
            "syncVersion": "1",
            "startDate": "2019-01-27 16:31:22 +0000",
            "quantity": "70 mg/dL",
            "isDisplayOnly": "false",
            "provenanceIdentifier": '"com.dexcom.G6"',
        },
        {
            "sampleUUID": "AFCF551E-BA6D-45A3-9507-18ADCC1F41EB",
            "syncIdentifier": '"AFCF551E-BA6D-45A3-9507-18ADCC1F41EB"',
            "syncVersion": "1",
            "startDate": "2019-01-27 16:36:22 +0000",
            "quantity": "71 mg/dL",
            "isDisplayOnly": "false",
            "provenanceIdentifier": '"com.dexcom.G6"',
        },
    ]


def get_glucose_store():
    return {
        "latestGlucoseValue": ' Optional(LoopKit.StoredGlucoseSample(sampleUUID: 7ED3FC10-0E37-4243-86F1-6E187E62F2DF, syncIdentifier: "00AA0A 2596408", syncVersion: 1, startDate: 2019-01-28 15:16:20 +0000, quantity: 85 mg/dL, isDisplayOnly: false, provenanceIdentifier: ""))',
        "managedDataInterval": " 10800.0",
        "cacheLength": " 86400.0",
        "momentumDataInterval": " 900.0",
        "observerQuery": " Optional(<HKObserverQuery:0x2838d4e80 active>)",
        "observationStart": " 2019-01-27 10:20:09 +0000",
        "observationEnabled": " true",
        "authorizationRequired": " false",
        "latest_glucose_value": {
            "sampleUUID": " 7ED3FC10-0E37-4243-86F1-6E187E62F2DF",
            "syncIdentifier": ' "00AA0A 2596408',
            "syncVersion": " 1",
            "startDate": " 2019-01-28 15",
            "quantity": " 85 mg/dL",
            "isDisplayOnly": " false",
            "provenanceIdentifier": " ",
        },
    }


def get_persistence_controller():
    return {
        "isReadOnly": " false",
        "directoryURL": " file:///private/var/mobile/Containers/Shared/AppGroup/8BC29390-EA20-4B3E-AB35-4AFB9CA53A94/com.loopkit.LoopKit/",
        "persistenceStoreCoordinator": " Optional(<NSPersistentStoreCoordinator: 0x280389140>)",
    }


def get_riley_link_device_manager():
    return {
        "central": " <CBCentralManager: 0x28039c140>",
        "autoConnectIDs": ' ["3F390A3A-9BEC-D2E4-08D7-13D13BDF4672"]',
        "timerTickEnabled": " false",
        "idleListeningState": " enabled(timeout: 240.0, channel: 0)",
    }


def get_g5_cgm_manager():
    return {
        "transmitter": " Optional(CGMBLEKit.Transmitter)",
        "providesBLEHeartbeat": " true",
        "latestReading": {
            "glucoseMessage": {
                "timestamp": " 2596408",
                "glucoseIsDisplayOnly": " false",
                "glucose": " 85",
                "trend": " -1",
            },
            "timeMessage": {
                "status": " 0",
                "currentTime": " 2596413",
                "sessionStartTime": " 1820222",
            },
            "transmitterID": ' "00AA0A',
            "status": " CGMBLEKit.TransmitterStatus.ok",
            "sessionStartDate": " 2019-01-19 15",
            "lastCalibration": " nil",
            "readDate": " 2019-01-28 15",
        },
    }
