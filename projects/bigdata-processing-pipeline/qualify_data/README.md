# qualify-data
Python code for qualifying donated data.

* **tidepool-qualification-criteria.json**
  * A set of criteria are used as follows:
    * **"name"** _(string)_ - Used in the naming of metadata and files (default: "Tidepool")
    * **"nTempBasalsPerDayIsClosedLoop"** _(int)_ - The minimum number of temporary basal rates set by an insulin pump to be considered a 'closed loop' system (default: 30)
    * **"timeFreqMin"** _(int)_ -  The frequency, in minutes, of continuous glucose monitor data. (default: 5)
    * **"bolusesPerDay**" _(int)_ -  The average number of boluses given in a day (default: 1)
    * **"cgmPercentPerDay"** _(float)_ - The percent of CGM usage (default: 0.5)
    * **"tierAbbr"** _(string)_ - The abbreviation used to determine tier names. (default: "T")
    * **"tierNames"** _(string array)_ - The set of tier names, each corresponding to the array of other settings in this file. Single-element settings affect all tiers. (default: ["T1", "T2", "T3", "T4", "T5"])
    * **"minContiguousDays"** _(int array)_ -  The minimum days of data which contain more than the specified ratio of missing data (in maxGaptoContigRatio). (default: [30, 100, 200, 365, 730])
    * **"avgBolusCalcsPerDay"** _(int array)_ -  The average number of boluses which used the pump's onboard calculator to be administered. (default: [0, 0, 0, 0, 0])
    * **"percentDaysQualifying"** _(int array)_ -  The percent of days in a given time series which qualify on all other metrics to be accepted. (default: [80, 80, 80, 80, 80])
    * **"maxGapToContigRatio"** _(int array)_ - The maximum ratio of missing data to contiguous data. For example, out of 100 days of data, at most 10 days could be missing data before being disqualified. (default: [10, 10, 10, 10, 10])
* **qualify_single_dataset.py**
  * Requests the userid of the PHI file downloaded from get-donor-data tools
  * Creates a data/qualified-by-[name]-criteria folder with two subfolders:
    * dayStats - Each csv saved here contains the qualifying statistics of every day within a dataset.
    * metadata - Each csv saved here contains the total qualified state of an entire dataset.
* **qualify_all_donor_data_batch_process.py**
  * Loads in data/<uniqueDonorList.csv> file
  * Passes each userid to qualify_sing_dataset.py
  * Creates a data/PHI-[timestamp]-qualification-metadata.csv with a summary of all qualified states of all datasets in uniqueDonorList.

## dependencies:
* set up tidepool-analytics virtual environment (see /data-analytics/readme.md)
* requires that data is in the format output from the get-donor-data tools
* requires a json file with qualifying criteria. For Tidepool Employees looking for
data partner qualifying criteria see Big Data Vault in 1PSWD.

## TODO:
- [ ] account for 15 minute libre data, most likely change will be to change
  timeFreqMin to 15, but it could affect the number of
  boluses per day...HOWEVER, THIS CAN BE AVOIDED IF WE CHANGE FROM MERGING AT THE
  5 OR 15 MINUTE LEVEL, AND RATHER MERGE AT THE DAY LEVEL.
- [ ] add version number to the qualification results so that we can keep track
  of which qualification scripts were used to qualify the datasets. Figure out
  how to get version number from the header
- [ ] get the description from the header and add to argparse
- [ ] add everything up to the contiguous data to the flatten-json script, and
  start this file at the point of loading the contiguous data, it should
  significantly speed up the qualification process
- [ ] update variable names to be shorter and possibily more descriptive
- [ ] remove deprecated code
