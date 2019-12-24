
from tidals.load.load import load_data
import pandas as pd


def test_load_data_csv(current_path_load):
    check_data = [["one", "11/20/18 0:00", 74857],
                   ["two", "11/19/18 23:55", 968225],
                   ["three", "11/19/18 23:30", 946412],
                   ["four", "11/19/18 23:20", 536377]]
    check_dataframe = pd.DataFrame(check_data, columns=['string', 'datetime', "number"])
    output_dataframe, file_name = load_data(current_path_load + "/raw_data.csv")

    column_count = 3
    row_count = 4

    pd.testing.assert_frame_equal(output_dataframe, check_dataframe)
    assert(column_count == output_dataframe.shape[1])
    assert(row_count == output_dataframe.shape[0])
    assert(file_name == 'raw_data')


def test_load_data_json(current_path_load):
    check_data = [["one", pd.to_datetime("2018-11-20 00:00:00"), 74857],
                  ["two", pd.to_datetime("2018-11-19 23:55:00"), 968225],
                  ["three", pd.to_datetime("2018-11-19 23:30:00"), 946412],
                  ["four", pd.to_datetime("2018-11-19 23:20:00"), 536377]]
    check_dataframe = pd.DataFrame(check_data, columns=['string', 'datetime', "number"])
    output_dataframe, file_name = load_data(current_path_load + "/raw_data.json")

    column_count = 3
    row_count = 4

    pd.testing.assert_frame_equal(output_dataframe, check_dataframe)
    assert(column_count == output_dataframe.shape[1])
    assert(row_count == output_dataframe.shape[0])
    assert (file_name == 'raw_data')


def test_load_data_xlsx(current_path_load):
    check_data = [[1, "one", pd.to_datetime("11/20/18 0:00"), 74857],
                   [2, "two", pd.to_datetime("11/19/18 23:55"), 968225],
                   [3, "three", pd.to_datetime("11/19/18 23:30"), 946412],
                   [4, "four", pd.to_datetime("11/19/18 23:20"), 536377]]
    check_dataframe = pd.DataFrame(check_data, columns=['jsonRowIndex', 'string', 'datetime', "number"])
    check_dataframe = check_dataframe.set_index('jsonRowIndex')
    output_dataframe, file_name = load_data(current_path_load + "/raw_data.xlsx")

    column_count = 3
    row_count = 4

    pd.testing.assert_frame_equal(output_dataframe, check_dataframe)
    assert(column_count == output_dataframe.shape[1])
    assert(row_count == output_dataframe.shape[0])
    assert(file_name == 'raw_data')












