
from tidals.clean.clean import remove_duplicates, round_time, flatten_json
import pandas as pd
from pandas.util import testing as tm
import pytest
import os



def test_remove_duplicates(valid_df):

    duplicated_data =  [["jjety", "AB9960", "response1", "response2", "Sun Nov 19 23:59:59 2018", pd.to_datetime("2018-11-20 00:00:00")],
                  ["jjety", "AB9958", "response1", "response2", "Sun Nov 19 23:56:59 2018", pd.to_datetime("2018-11-19 23:55:00")],
                  ["hqoh", "AB9953", "response1", "response2", "Sun Nov 19 23:29:59 2018", pd.to_datetime("2018-11-19 23:30:00")],
                  ["hhawe", "AB8769", "response1", "response2", "Sun Nov 19 23:20:01 2018", pd.to_datetime("2018-11-19 23:20:00")],
                  ["hhawe", "AB8769", "response1", "response2", "Sun Nov 19 23:20:01 2018", pd.to_datetime("2018-11-19 23:20:00")]]

    duplicated_df = pd.DataFrame(duplicated_data, columns=['userID', 'studyID',"getData.response1", "getData.response2", "time", "roundedTime"])
    pandas_drop_df = duplicated_df.drop_duplicates('time')

    clean_df, duplicate_count = remove_duplicates(duplicated_df, duplicated_df["time"])

    tm.assert_frame_equal(valid_df, clean_df)
    tm.assert_frame_equal(valid_df, pandas_drop_df)
    assert duplicate_count == 1


def test_round_time(valid_df):
    raw_data = [["hhawe", "AB8769", "response1", "response2", "Sun Nov 19 23:20:01 2018"],
                  ["hqoh", "AB9953", "response1", "response2", "Sun Nov 19 23:29:59 2018"],
                  ["jjety", "AB9958", "response1", "response2", "Sun Nov 19 23:56:59 2018"],
                  ["jjety", "AB9960", "response1", "response2", "Sun Nov 19 23:59:59 2018"]]


    raw_df = pd.DataFrame(raw_data, columns=['userID', 'studyID', "getData.response1", "getData.response2", "time"])
    rounded_df = round_time(raw_df)
    tm.assert_frame_equal(valid_df, rounded_df)


def test_round_time_across_month(valid_df):
    raw_data = [["hhawe", "AB8769", "newyear", "response2", "2018-11-30 23:59:10"]]
    raw_df = pd.DataFrame(raw_data, columns=['userID', 'studyID', "getData.response1", "getData.response2", "time"])
    rounded_df = round_time(raw_df)
    expected_time = pd.Timestamp('2018-12-01')

    rounded_new_year = rounded_df.iloc[0]['roundedTime']
    assert( pd.Timestamp(rounded_new_year) == expected_time)


def test_round_time_across_year():
    raw_data = [["hhawe", "AB8769", "newyear", "response2", "2018-12-31 23:59:10"]]
    raw_df = pd.DataFrame(raw_data, columns=['userID', 'studyID', "getData.response1", "getData.response2", "time"])
    rounded_df = round_time(raw_df)
    expected_time = pd.Timestamp('2019-01-01')

    rounded_new_year = rounded_df.iloc[0]['roundedTime']
    assert( pd.Timestamp(rounded_new_year) == expected_time)


def test_round_time_early_hour():
    raw_data = [["hhawe", "AB8769", "newyear", "response2", "2018-11-29 00:01:10"]]
    raw_df = pd.DataFrame(raw_data, columns=['userID', 'studyID', "getData.response1", "getData.response2", "time"])
    rounded_df = round_time(raw_df)
    expected_time = pd.Timestamp('2018-11-29')

    rounded_new_year = rounded_df.iloc[0]['roundedTime']
    assert( pd.Timestamp(rounded_new_year) == expected_time)


def test_round_invalid_date():
    raw_data = [["hhawe", "AB8769", "newyear", "response2", "2018-11-31 00:01:10"]]
    raw_df = pd.DataFrame(raw_data, columns=['userID', 'studyID', "getData.response1", "getData.response2", "time"])
    with pytest.raises(ValueError) as excinfo:
        round_time(raw_df)

    assert("day is out of range for month" == excinfo.value.args[0])

def test_round_invalid_time():
    raw_data = [["hhawe", "AB8769", "newyear", "response2", "2018-11-31 25:01:10"]]
    raw_df = pd.DataFrame(raw_data, columns=['userID', 'studyID', "getData.response1", "getData.response2", "time"])
    with pytest.raises(ValueError) as excinfo:
        round_time(raw_df)

    print("path11", os.getcwd())
    assert("day is out of range for month" == excinfo.value.args[0])

@pytest.mark.skip(reason='need a valid dataframe example')
def test_flatten_json():
    df = pd.read_csv('')
    flattened_df = flatten_json(df)







