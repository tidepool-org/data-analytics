import pytest
import pandas as pd


@pytest.fixture()
def valid_df():
    check_data =  [["jjety", "AB9960", "response1", "response2", "Sun Nov 19 23:59:59 2018", pd.to_datetime("2018-11-20 00:00:00")],
     ["jjety", "AB9958", "response1", "response2", "Sun Nov 19 23:56:59 2018", pd.to_datetime("2018-11-19 23:55:00")],
     ["hqoh", "AB9953", "response1", "response2", "Sun Nov 19 23:29:59 2018", pd.to_datetime("2018-11-19 23:30:00")],
     ["hhawe", "AB8769", "response1", "response2", "Sun Nov 19 23:20:01 2018", pd.to_datetime("2018-11-19 23:20:00")]]

    valid_df = pd.DataFrame(check_data, columns=['userID', 'studyID', "getData.response1", "getData.response2", "time", "roundedTime"])

    return valid_df
