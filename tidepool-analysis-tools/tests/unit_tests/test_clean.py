
from tidals.clean.clean import remove_duplicates, round_time
import pandas as pd
from pandas.util import testing as tm
import pytest
from tests.fixtures.clean_setup import valid_df


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

