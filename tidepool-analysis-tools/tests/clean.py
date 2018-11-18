
from clean.clean import remove_duplicates
import pandas as pd
from pandas.util import testing as tm


def test_remove_duplicates():
    df_check = pd.DataFrame([1, 2, 3, 4, 5])
    df_duplicates = pd.DataFrame([1, 2, 3, 3, 4, 5])
    df_clean=df_duplicates.drop_duplicates()

    df_clean, count = remove_duplicates(df_duplicates, df_duplicates)

    tm.assert_frame_equal(df_check, df_clean)