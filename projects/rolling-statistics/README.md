# Rolling Statistics
A script to calculate and visualize rolling statistics of cgm and pump data from Tidepool.

## Usage
**rolling_statistics.py** arguments:  
`-i`:  Input filename of a .csv to analyze (default: "", no input will ask for a Tidepool account login)

`-years`: Number of years of data to retrieve (default: 10)

`-rw`: An array of rolling window strings or 'continuous' option. (default: ["1day", "3day", "7day", "14day", "21day", "30day", "60day", "90day", "180day", "365day"]) 

`-viz`: True/False whether to output plotly visualization of data (default: True)



Example Call:
`python rolling_statistics.py -years 1 -rw continuous`

##Output:

All output is stored in a `results` folder.

This includes the files `daily_rolling_stats_user_id.csv` and `rollng-stats-daily-viz.html` (if visualization is set to True).

## Dependencies:
* set up tidepool-analytics virtual environment (see /data-analytics/readme.md)

## TODO:

* Add list of metrics to README (see rolling_stats.py for full list)
* Add mmol/l conversions for metrics
* Add support for Freestyle Libre data and custom data frequency
* Add rolling statistics for insulin pump data
  * Mean Daily Total Basal
  * Mean Daily Total Bolus
  * Mean Daily Basal Count
  * Mean Daily Carbs



