#from projects.parsers.loop_report import LoopReport
import projects.parsers.loop_report as loop_report
import os
import pytest


def test_parse_by_file():
    lr = loop_report.LoopReport()
    loop_dict = lr.parse_by_file(os.getcwd() + "/files", 'LoopReport.md')
    assert loop_dict["file_name"] == 'LoopReport.md'
    assert loop_dict["loop_version"] == 'Loop v1.9.3'
    assert loop_dict['rileyLink_radio_firmware'] == 'Optional(subg_rfspy 0.9)'
    assert loop_dict['rileyLink_ble_firmware'] == 'Optional(ble_rfspy 0.9)'
    assert loop_dict['carb_ratio_unit'] == 'g'
    assert loop_dict['carb_ratio_timeZone'] == -28800

    carb_ratio_schedule = [{'startTime': 0.0, 'value': 10.0}, {'startTime': 66600.0, 'value': 9.0}]
    assert loop_dict['carb_ratio_schedule'] == carb_ratio_schedule
    assert loop_dict['carb_default_absorption_times_fast'] == 1800.0
    assert loop_dict['carb_default_absorption_times_medium'] == 10800.0
    assert loop_dict['carb_default_absorption_times_slow'] == 18000.0
    insulin_sensitivity_factor_schedule = [{'startTime': 0.0, 'value': 20.0}, {'startTime': 9000.0, 'value': 40.0}, {'startTime': 82800.0, 'value': 35.0}]
    assert loop_dict['insulin_sensitivity_factor_schedule'] == insulin_sensitivity_factor_schedule

    assert loop_dict['insulin_sensitivity_factor_timeZone'] == -28800
    assert loop_dict['insulin_sensitivity_factor_unit'] == 'mg/dL'
    assert loop_dict['basal_rate_timeZone'] == -28800
    basal_rate_schedule = [{'startTime': 0.0, 'value': 0.8}, {'startTime': 23400.0, 'value': 0.8}, {'startTime': 72000.0, 'value': 0.6}]
    assert loop_dict['basal_rate_schedule'] == basal_rate_schedule
    assert loop_dict['insulin_model'] == 'humalogNovologAdult'
    assert loop_dict['insulin_action_duration'] == 21600.0
    assert loop_dict['pump_manager_type'] == 'minimed'
    assert loop_dict['pump_model'] == '723'
    assert loop_dict['maximum_basal_rate'] == 4.0
    assert loop_dict['maximum_bolus'] == 10.0
    assert loop_dict['retrospective_correction_enabled'] == 'true'
    assert loop_dict['suspend_threshold'] == 85.0
    assert loop_dict['suspend_threshold_unit'] == 'mg/dL'
    override_range_workout = [135.0, 145.0]
    assert loop_dict['override_range_workout'] == override_range_workout
    override_range_premeal = [70.0, 80.0]
    assert loop_dict['override_range_premeal'] == override_range_premeal
    assert loop_dict['insulin_counteration_effects'].to_dict() == get_insulin_counteration_effects()
    assert loop_dict['retrospective_glucose_discrepancies_summed'].to_dict() == get_retrospective_glucose_discrepancies_summed()
    assert loop_dict['insulin_counteraction_effects'].to_dict() == get_insulin_counteraction_effects()
    assert loop_dict['get_reservoir_values'].to_dict() == get_reservoir_values()
    assert loop_dict['predicted_glucose'].to_dict() == get_predicted_glucose()
    assert loop_dict['retrospective_glucose_discrepancies'].to_dict() == get_retrospective_glucose_discrepancies()
    assert loop_dict['carb_effect'].to_dict() == get_carb_effect()
    assert loop_dict['insulin_effect'].to_dict() == get_insulin_effect()
    assert loop_dict['get_normalized_pump_even_dose'].to_dict() == get_normalized_pump_even_dose()
    assert loop_dict['get_normalized_dose_entries'].to_dict() == get_normalized_dose_entries()
    assert loop_dict['cached_dose_entries'].to_dict() == get_cached_dose_entries()
    assert loop_dict['get_pump_event_values'].shape[0] == 19
    assert loop_dict['get_pump_event_values'].shape[1] == 22
    assert loop_dict['message_log'] == get_message_log()
    assert loop_dict['g5_cgm_manager'] == get_g5_cgm_manager()
    assert loop_dict['dex_cgm_manager'] == {'shareManager': ' Optional(## ShareClientManager', 'latestBackfill': ' nil', ')': ')'}
    assert loop_dict['riley_link_pump_manager'] == {'rileyLinkConnectionManager': ' Optional(RileyLinkBLEKit.RileyLinkConnectionManager)', 'lastTimerTick': ' 2019-01-28 14:26:19 +0000'}
    assert loop_dict['riley_link_device_manager'] == get_riley_link_device_manager()
    assert loop_dict['persistence_controller'] == get_persistence_controller()
    assert loop_dict['glucose_store'] == get_glucose_store()
    assert loop_dict['cached_glucose_samples'].to_dict() == get_cached_glucose_samples()
    assert loop_dict['cached_carb_entries'].to_dict() == get_cached_carb_entries()
    assert loop_dict['insulin_delivery_store'] == get_insulin_delivery_store()


def test_parse_by_directory():
    lr = loop_report.LoopReport()
    list_of_files = lr.parse_by_directory(os.path.realpath('files'))
    assert len(list_of_files) == 2


def test_parse_by_file_missing_file_name():
    with pytest.raises(RuntimeError) as excinfo:
        lr = loop_report.LoopReport()
        lr.parse_by_file(os.getcwd() + "/files", '')
    assert 'The file path or file name passed in is invalid.' in str(excinfo.value)


def test_parse_by_file_invalid_directory():
    with pytest.raises(RuntimeError) as excinfo:
        lr = loop_report.LoopReport()
        lr.parse_by_file("", 'test_loop_report.py')
    assert 'The file path or file name passed in is invalid.' in str(excinfo.value)


def test_parse_by_directory_invalid_directory():
    with pytest.raises(RuntimeError) as excinfo:
        lr = loop_report.LoopReport()
        lr.parse_by_directory("")
    assert 'The directory passed in is invalid.' in str(excinfo.value)


def get_insulin_counteraction_effects():
    return {'start_time': {0: '2019-01-27 15:21:22 +0000', 1: '2019-01-27 15:26:22 +0000', 2: '2019-01-27 15:31:22 +0000',
                    3: '2019-01-27 15:36:22 +0000', 4: '2019-01-27 15:41:22 +0000', 5: '2019-01-27 15:46:22 +0000',
                    6: '2019-01-27 15:51:21 +0000', 7: '2019-01-27 15:56:22 +0000', 8: '2019-01-27 16:01:22 +0000',
                    9: '2019-01-27 16:06:22 +0000', 10: '2019-01-27 16:11:22 +0000', 11: '2019-01-27 16:16:22 +0000',
                    12: '2019-01-27 16:21:22 +0000'},
     'end_time': {0: ' 2019-01-27 15:26:22 +0000', 1: ' 2019-01-27 15:31:22 +0000', 2: ' 2019-01-27 15:36:22 +0000',
                  3: ' 2019-01-27 15:41:22 +0000', 4: ' 2019-01-27 15:46:22 +0000', 5: ' 2019-01-27 15:51:21 +0000',
                  6: ' 2019-01-27 15:56:22 +0000', 7: ' 2019-01-27 16:01:22 +0000', 8: ' 2019-01-27 16:06:22 +0000',
                  9: ' 2019-01-27 16:11:22 +0000', 10: ' 2019-01-27 16:16:22 +0000', 11: ' 2019-01-27 16:21:22 +0000',
                  12: ' 2019-01-27 16:26:22 +0000'},
     'value': {0: ' 0.11340556858587406', 1: ' -0.09644491407321425', 2: ' -0.5038144363643894',
               3: ' 0.09110549888380319', 4: ' 0.08806492424520086', 5: ' 0.2877941626511216',
               6: ' -0.11365967464421017', 7: ' -0.3170549421296755', 8: ' -0.12201958445077564',
               9: ' -0.1286808487354534', 10: ' -0.5368095386319524', 11: ' -0.9461971753678154',
               12: ' -0.9566544114980243'}}


def get_retrospective_glucose_discrepancies_summed():
    return {
        'start_time': {0: '2018-11-28 00:02:31 +0000', 1: '2018-11-28 00:02:31 +0000', 2: '2018-11-28 00:02:31 +0000',
                       3: '2018-11-28 00:02:31 +0000', 4: '2018-11-28 00:02:31 +0000', 5: '2018-11-28 00:02:31 +0000',
                       6: '2018-11-28 00:02:31 +0000'},
        'end_time': {0: ' 2018-11-28 00:02:31 +0000', 1: ' 2018-11-28 00:07:31 +0000', 2: ' 2018-11-28 00:12:31 +0000',
                     3: ' 2018-11-28 00:17:31 +0000', 4: ' 2018-11-28 00:22:31 +0000', 5: ' 2018-11-28 00:27:31 +0000',
                     6: ' 2018-11-28 00:32:31 +0000'},
        'value': {0: ' 13.150577197081377', 1: ' 26.06978171944507', 2: ' 38.67818952118729', 3: ' 49.22323442360305',
                  4: ' 57.644897625857766', 5: ' 64.15869871324333', 6: ' 67.1655997352358'}}


def get_insulin_counteration_effects():
    return {
        'start_time': {0: '2019-01-27 15:16:22 +0000', 1: '2019-01-27 15:21:22 +0000', 2: '2019-01-27 15:26:22 +0000',
                       3: '2019-01-27 15:31:22 +0000', 4: '2019-01-27 15:36:22 +0000', 5: '2019-01-27 15:41:22 +0000',
                       6: '2019-01-27 15:46:22 +0000', 7: '2019-01-27 15:51:21 +0000', 8: '2019-01-27 15:56:22 +0000',
                       9: '2019-01-27 16:01:22 +0000', 10: '2019-01-27 16:06:22 +0000', 11: '2019-01-27 16:11:22 +0000',
                       12: '2019-01-27 16:16:22 +0000', 13: '2019-01-27 16:21:22 +0000',
                       14: '2019-01-27 16:26:22 +0000'},
        'end_time': {0: ' 2019-01-27 15:21:22 +0000', 1: ' 2019-01-27 15:26:22 +0000', 2: ' 2019-01-27 15:31:22 +0000',
                     3: ' 2019-01-27 15:36:22 +0000', 4: ' 2019-01-27 15:41:22 +0000', 5: ' 2019-01-27 15:46:22 +0000',
                     6: ' 2019-01-27 15:51:21 +0000', 7: ' 2019-01-27 15:56:22 +0000', 8: ' 2019-01-27 16:01:22 +0000',
                     9: ' 2019-01-27 16:06:22 +0000', 10: ' 2019-01-27 16:11:22 +0000',
                     11: ' 2019-01-27 16:16:22 +0000', 12: ' 2019-01-27 16:21:22 +0000',
                     13: ' 2019-01-27 16:26:22 +0000', 14: ' 2019-01-27 16:31:22 +0000'},
        'value': {0: ' 0.12323223579096947', 1: ' 0.11340556858587406', 2: ' -0.09644491407321425',
                  3: ' -0.5038144363643894', 4: ' 0.09110549888380319', 5: ' 0.08806492424520086',
                  6: ' 0.2877941626511216', 7: ' -0.11365967464421017', 8: ' -0.3170549421296755',
                  9: ' -0.12201958445077564', 10: ' -0.1286808487354534', 11: ' -0.5368095386319524',
                  12: ' -0.9461971753678154', 13: ' -0.9566544114980243', 14: ' -0.1680095551964925'}}


def get_message_log():
    return ['2019-01-08 18:42:00 +0000 send 1f0d624118030e01008179',
     '2019-01-08 18:42:02 +0000 receive 1f0d62411c0a1d2803c0a000003d9bff81b4',
     '2019-01-08 18:46:07 +0000 send 1f0d624120030e010002cd',
     '2019-01-08 18:46:09 +0000 receive 1f0d6241240a1d2803c1a000003dabff0342',
     '2019-01-08 18:46:11 +0000 send 1f0d624128071f054c4d1dbb0280ff',
     '2019-01-08 18:46:14 +0000 receive 1f0d62412c0a1d1803c1d000003dabff82a6']


def get_pump_event_values():
    return {'date': "{0: '2019-01-28 13:56:27 +0000'}", 'description': "{0: nan}", 'dose': "{0: 'nil'}", 'duration': '{0: nan}',
     'endDate': '{0: nan}', 'isUploaded': "{0: 'false'}",
     'objectIDURL': "{0: 'x-coredata://17F97154-93F5-49F8-9870-B15219F6980C/PumpEvent/p50068'}",
     'persistedDate': "{0: '2019-01-28 14:01:58 +0000'}", 'rate': "{0: '0.375'}",
     'rateType': "{0: 'MinimedKit.TempBasalPumpEvent.RateType.Absolute'}", 'raw': "{0: 'Optional(8 bytes'}",
     'rawData': "{0: '8 bytes'}", 'scheduleEntry': '{0: nan}', 'scheduledBasalRate': '{0: nan}', 'startDate': '{0: nan}',
     'syncIdentifier': '{0: nan}', 'timeOffset': '{0: nan}', 'timestamp': "{0: 'calendar'}",
     'title': '{0: \'Optional("TempBasalPumpEvent(length\'}', 'type': "{0: 'nil'}", 'unit': '{0: nan}', 'value': '{0: nan}'}


def get_cached_dose_entries():
    return {'type': {0: 'LoopKit.DoseType.basal'}, 'startDate': {0: '2019-01-07 21:26:00 +0000'},
     'endDate': {0: '2019-01-07 21:26:08 +0000'}, 'value': {0: '0.0'}, 'unit': {0: 'LoopKit.DoseUnit.units'},
     'description': {0: 'nil'},
     'syncIdentifier': {0: 'Optional("BasalRateSchedule 2019-01-07T21:26:00Z 2019-01-07T21:26:08Z"'},
     'scheduledBasalRate': {0: 'nil'}}


def get_normalized_dose_entries():
    return {'type': {0: 'LoopKit.DoseType.basal'}, 'startDate': {0: '2019-01-25 04:51:24 +0000'},
     'endDate': {0: '2019-01-25 05:01:25 +0000'}, 'value': {0: '0.6'}, 'unit': {0: 'LoopKit.DoseUnit.unitsPerHour'},
     'description': {0: 'nil'}, 'syncIdentifier': {0: 'Optional("7b021873141813281800"'},
     'scheduledBasalRate': {0: 'nil'}}


def get_normalized_pump_even_dose():
    return {'type': {0: 'LoopKit.DoseType.basal'}, 'startDate': {0: '2019-01-27 18:26:42 +0000'},
     'endDate': {0: '2019-01-27 18:30:37 +0000'}, 'value': {0: '0.8'}, 'unit': {0: 'LoopKit.DoseUnit.unitsPerHour'},
     'description': {0: 'nil'}, 'syncIdentifier': {0: 'Optional("7b012a5a0a1b130d2000"'},
     'scheduledBasalRate': {0: 'nil'}}


def get_insulin_effect():
    return {'start_time': {0: '2018-11-28 00:30:00 +0000', 1: '2018-11-28 00:35:00 +0000', 2: '2018-11-28 00:40:00 +0000',
                    3: '2018-11-28 00:45:00 +0000', 4: '2018-11-28 00:50:00 +0000', 5: '2018-11-28 00:55:00 +0000',
                    6: '2018-11-28 01:00:00 +0000', 7: '2018-11-28 01:05:00 +0000', 8: '2018-11-28 01:10:00 +0000',
                    9: '2018-11-28 01:15:00 +0000'},
     'value': {0: ' -598.4414718881781', 1: ' -608.2232418870775', 2: ' -618.1781269950548', 3: ' -628.2362250846572',
               4: ' -638.3355211023576', 5: ' -648.4211533199497', 6: ' -658.4447024193285', 7: ' -668.3632968575748',
               8: ' -678.1394998374639', 9: ' -687.740877675081'}}


def get_carb_effect():
    return {'start_time': {0: '2018-11-28 00:00:00 +0000', 1: '2018-11-28 00:05:00 +0000', 2: '2018-11-28 00:10:00 +0000',
                    3: '2018-11-28 00:15:00 +0000', 4: '2018-11-28 00:20:00 +0000', 5: '2018-11-28 00:25:00 +0000',
                    6: '2018-11-28 00:30:00 +0000', 7: '2018-11-28 00:35:00 +0000', 8: '2018-11-28 00:40:00 +0000',
                    9: '2018-11-28 00:45:00 +0000', 10: '2018-11-28 00:50:00 +0000', 11: '2018-11-28 00:55:00 +0000',
                    12: '2018-11-28 01:00:00 +0000'},
     'value': {0: ' 309.375', 1: ' 309.375', 2: ' 309.375', 3: ' 309.375', 4: ' 309.375', 5: ' 309.375', 6: ' 309.375',
               7: ' 313.1571581860383', 8: ' 320.79604707492723', 9: ' 328.4349359638161', 10: ' 336.073824852705',
               11: ' 343.7127137415939', 12: ' 351.3516026304828'}}


def get_retrospective_glucose_discrepancies():
    return {'start_time': {0: '2018-11-28 00:02:31 +0000', 1: '2018-11-28 00:07:31 +0000', 2: '2018-11-28 00:12:31 +0000',
                    3: '2018-11-28 00:17:31 +0000', 4: '2018-11-28 00:22:31 +0000', 5: '2018-11-28 00:27:31 +0000',
                    6: '2018-11-28 00:32:31 +0000'},
     'value': {0: ' 13.150577197081377', 1: ' 12.919204522363694', 2: ' 12.608407801742223', 3: ' 10.545044902415762',
               4: ' 8.421663202254713', 5: ' 6.513801087385557', 6: ' 3.0069010219924754'}}


def get_predicted_glucose():
    return {'start_time': {0: '2019-01-28 15:16:20 +0000', 1: '2019-01-28 15:20:00 +0000', 2: '2019-01-28 15:25:00 +0000',
                    3: '2019-01-28 15:30:00 +0000', 4: '2019-01-28 15:35:00 +0000', 5: '2019-01-28 15:40:00 +0000',
                    6: '2019-01-28 15:45:00 +0000', 7: '2019-01-28 15:50:00 +0000', 8: '2019-01-28 15:55:00 +0000',
                    9: '2019-01-28 16:00:00 +0000', 10: '2019-01-28 16:05:00 +0000', 11: '2019-01-28 16:10:00 +0000'},
     'value': {0: ' 85.0', 1: ' 85.732078872579', 2: ' 86.44096256310476', 3: ' 86.77019751074303',
               4: ' 86.74103998552496', 5: ' 86.64342159003903', 6: ' 86.57898055151605', 7: ' 86.54829897295224',
               8: ' 86.5520006409324', 9: ' 86.59083783299144', 10: ' 86.66555585381998', 11: ' 86.77683520191353'}}


def get_reservoir_values():
    return {'start_time': {0: '2019-01-28 15:16:00 +0000', 1: '2019-01-28 15:11:00 +0000', 2: '2019-01-28 15:06:00 +0000',
                    3: '2019-01-28 15:01:00 +0000', 4: '2019-01-28 14:56:00 +0000', 5: '2019-01-28 14:51:00 +0000',
                    6: '2019-01-28 14:46:00 +0000', 7: '2019-01-28 14:41:00 +0000', 8: '2019-01-28 14:36:00 +0000',
                    9: '2019-01-28 14:31:00 +0000', 10: '2019-01-28 14:26:00 +0000', 11: '2019-01-28 14:21:00 +0000',
                    12: '2019-01-28 14:16:00 +0000'},
     'value': {0: ' 168.9', 1: ' 168.9', 2: ' 168.9', 3: ' 168.9', 4: ' 169.0', 5: ' 169.1', 6: ' 169.1', 7: ' 169.2',
               8: ' 169.3', 9: ' 169.3', 10: ' 169.4', 11: ' 169.5', 12: ' 169.5'}}


def get_cached_carb_entries():
    return {'sampleUUID': {0: ' 2C030171-3604-4542-B492-9990AF375546'},
     'syncIdentifier': {0: ' 7FF9C039-BE6E-4479-BE4C-3F7EAC1ECF34'}, 'syncVersion': {0: ' 1'},
     'startDate': {0: ' 2019-01-28 05:41:22 +0000'}, 'quantity': {0: ' 7 g'}, 'foodType': {0: ' '},
     'absorptionTime': {0: ' 10800.0'}, 'createdByCurrentApp': {0: ' true'},
     'externalID': {0: ' 5c4e9604d8dfb37103e428d1'}, 'isUploaded': {0: ' true'}}


def get_insulin_delivery_store():
    return {'observerQuery': ' Optional(<HKObserverQuery:0x2838f1180 active>)',
     'observationStart': ' 2019-01-28 04:20:09 +0000', 'observationEnabled': ' true', 'authorizationRequired': ' false',
     'lastBasalEndDate': ' 2019-01-28 10:06:28 +0000'}


def get_cached_glucose_samples():
    return {'sampleUUID': {0: 'AFCF551E-BA6D-45A3-9507-18ADCC1F41EB'},
     'syncIdentifier': {0: '"AFCF551E-BA6D-45A3-9507-18ADCC1F41EB"'}, 'syncVersion': {0: '1'},
     'startDate': {0: '2019-01-27 16:36:22 +0000'}, 'quantity': {0: '71 mg/dL'}, 'isDisplayOnly': {0: 'false'},
     'provenanceIdentifier': {0: '"com.dexcom.G6"'}}


def get_glucose_store():
    return {'latestGlucoseValue': ' Optional(LoopKit.StoredGlucoseSample(sampleUUID: 7ED3FC10-0E37-4243-86F1-6E187E62F2DF, syncIdentifier: "00AA0A 2596408", syncVersion: 1, startDate: 2019-01-28 15:16:20 +0000, quantity: 85 mg/dL, isDisplayOnly: false, provenanceIdentifier: ""))', 'managedDataInterval': ' 10800.0', 'cacheLength': ' 86400.0', 'momentumDataInterval': ' 900.0', 'observerQuery': ' Optional(<HKObserverQuery:0x2838d4e80 active>)', 'observationStart': ' 2019-01-27 10:20:09 +0000', 'observationEnabled': ' true', 'authorizationRequired': ' false'}


def get_persistence_controller():
    return {'isReadOnly': ' false',
     'directoryURL': ' file:///private/var/mobile/Containers/Shared/AppGroup/8BC29390-EA20-4B3E-AB35-4AFB9CA53A94/com.loopkit.LoopKit/',
     'persistenceStoreCoordinator': ' Optional(<NSPersistentStoreCoordinator: 0x280389140>)'}


def get_riley_link_device_manager():
    return {'central': ' <CBCentralManager: 0x28039c140>', 'autoConnectIDs': ' ["3F390A3A-9BEC-D2E4-08D7-13D13BDF4672"]',
     'timerTickEnabled': ' false', 'idleListeningState': ' enabled(timeout: 240.0, channel: 0)'}


def get_g5_cgm_manager():
    return {
        'latestReading': ' Optional(CGMBLEKit.Glucose(glucoseMessage: CGMBLEKit.GlucoseSubMessage(timestamp: 2596408, glucoseIsDisplayOnly: false, glucose: 85, state: 6, trend: -1), timeMessage: CGMBLEKit.TransmitterTimeRxMessage(status: 0, currentTime: 2596413, sessionStartTime: 1820222), transmitterID: "00AA0A", status: CGMBLEKit.TransmitterStatus.ok, sessionStartDate: 2019-01-19 15:39:54 +0000, lastCalibration: nil, readDate: 2019-01-28 15:16:20 +0000))',
        'transmitter': ' Optional(CGMBLEKit.Transmitter)', 'providesBLEHeartbeat': ' true'}


