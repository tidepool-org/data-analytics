#from projects.parsers.loop_report import LoopReport
import projects.parsers.loop_report as loop_report
import os
import pytest


def test_parse_by_file():
    lr = loop_report.LoopReport()
    loop_dict = lr.parse_by_file(os.getcwd() + "/files", 'LoopReport.md')

    valid_loop_report_dict = {'file_name': 'LoopReport.md',
                              'loop_version': 'Loop v1.9.3',
                              'rileyLink_radio_firmware':
                                  'Optional(subg_rfspy 0.9)',
                              'rileyLink_ble_firmware': 'Optional(ble_rfspy 0.9)',
                              'carb_ratio_unit': 'g',
                              'carb_ratio_timeZone': -28800,
                              'carb_ratio_schedule': [{'startTime': 0.0, 'value': 10.0}, {'startTime': 66600.0, 'value': 9.0}],
                              'carb_default_absorption_times_fast': 1800.0,
                              'carb_default_absorption_times_medium': 10800.0,
                              'carb_default_absorption_times_slow': 18000.0,
                              'insulin_sensitivity_factor_schedule': [{'startTime': 0.0, 'value': 20.0}, {'startTime': 9000.0, 'value': 40.0}, {'startTime': 82800.0, 'value': 35.0}],
                              'insulin_sensitivity_factor_timeZone': -28800,
                              'insulin_sensitivity_factor_unit': 'mg/dL',
                              'basal_rate_timeZone': -28800,
                              'basal_rate_schedule': [{'startTime': 0.0, 'value': 0.8}, {'startTime': 23400.0, 'value': 0.8}, {'startTime': 72000.0, 'value': 0.6}],
                              'insulin_model': 'humalogNovologAdult',
                              'insulin_action_duration': 21600.0,
                              'pump_manager_type': 'minimed',
                              'pump_model': '723',
                              'maximum_basal_rate': 4.0,
                              'maximum_bolus': 10.0,
                              'retrospective_correction_enabled': 'true',
                              'suspend_threshold': 85.0,
                              'suspend_threshold_unit': 'mg/dL',
                              'override_range_workout': [135.0, 145.0],
                              'override_range_premeal': [70.0, 80.0]}

    assert loop_dict == valid_loop_report_dict



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

    





