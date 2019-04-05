# Rolling Statistics Test Data
This dataset can be used to verify the output of the rolling statistics functions

## Data Set Information

This is a hand-engineered dataset that containing 7 days of CGM data in the date range of `2019-01-1 06:00:00` to `2019-01-08 05:55:00`

Each day has a different CGM pattern and events that the rolling stats function should reflect. 

**Note 1**: A "day" starts at 6am and ends of 5:55am, consisting of 288 possible points.

**Note 2**: An "event" consists of 3 contiguous data points (15 minutes of data)

Here is the break down of each day:

|    Day     |                           Pattern                            |
| :--------: | :----------------------------------------------------------: |
| 2019-01-01 |                    288 points @ 100 mg/dL                    |
| 2019-01-02 |                    288 points @ 200 mg/dL                    |
| 2019-01-03 |                    288 points @ 60 mg/dL                     |
| 2019-01-04 |  202 points @ 100 mg/dL<br> (70.01% percent data available)  |
| 2019-01-05 |  201 points @ 300 mg/dL<br>(69.79% percent data available)   |
| 2019-01-06 | 3 events @ 60 mg/dL, 3 events @ 200 mg/dL<br>(all other points @ 100 mg/dL) |
| 2019-01-07 | 3 events @ 45 mg/dL, 3 events @ 300 mg/dL<br>(all other points @ 100 mg/dL) |



## Usage

This file is for manual analysis at this time.

Import normal modules and functions definitions, then run the following lines within the console:

```python
clean_cgm_df = pd.read_excel('test_data/test_rolling_stats.xlsx')
clean_cgm_df["est.localTime_rounded"] = pd.to_datetime(clean_cgm_df["est.localTime_rounded"])

rolling_df = get_rolling_stats(clean_cgm_df.copy(), args.rolling_windows)
daily_df = get_daily_stats(rolling_df)
```