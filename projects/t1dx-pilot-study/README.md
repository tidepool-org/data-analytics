# T1DX-Tidepool Pilot Study
This project contains the source code used in analyzing survey participant data uploaded to Tidepool as part of a pilot study conducted by T1DX (Type 1 Data Exchange).

The code is outlined as follows:

* Accept new participant data into T1DX study account
* Download participant data uploaded up until the survey start time
* Perform data QA (see below)
* Perform data analysis (see below)
* Output analysis file with survey participant metrics in each row

## Data Quality Assurance

The following data quality measures are taken before analysis:

* Removing invalid cgm values
* Flagging data with improper time settings using a local time estimate
* Removing data that was uploaded more than once

## Data Analysis

Metrics are calculated on the following time periods up to the time of the survey: 

* Past 7, 14, 30, 90, 365 days

* Past 7 days over the hours of 12AM-6AM (Sleep Disturbance)

The following core metrics are calculated:

* Mean glucose

* Percent time in ranges: 

    * Level 2 hypoglycemia (< 54 mg/dL)

    * Level 1 hypoglycemia (< 70 mg/dL)

    * Target Range (70-140 mg/dL & 70-180 mg/dL)

    * Level 1 hyperglycemia (> 180 mg/dL)

    * Level 2 hyperglycemia (> 250 mg/dL)

* Glycemic variability

    * Coefficient of variation (CV)

    * Standard deviation (SD)

    *  Percentiles: 10, 25, 50, 75, 90

    *  Range

    *  Absolute 

* Glycemic Management Indicator (GMI), and formerly referred to as estimated A1C (eA1c)
* Episodes of hypoglycemia and hyperglycemia defined by at least 15 minutes of contiguous readings below the Level 1 and Level 2 thresholds as noted above (i.e., < 54, < 70, > 180, > 250 mg/dL)
* Area-under-the-curve (AUC) for in range, mild/moderate/severe/overall hyper/hypoglycemia
* LBGI/HBGI (low/high blood glucose index)

Additional Metrics that might be explored:

* MAGE (mean amplitude of glycemic excursions) 
* ADRR (average daily risk ratio)
* CONGA (continuous overlapping net glycemic action) 
* GRADE (glycemic risk assessment in diabetes equation)
* CV of log-transformed blood glucose readings 
* J-Index 
* LI (lability index)
* MAG (mean absolute glucose)
* M-Value 
* MODD (mean of daily differences)

## dependencies:

- A tidepool-analytics virtual environment (see /data-analytics/readme.md)
- `.env` file with study account credentials with form:
  - EMAIL=
  - PASS=
  - SALT=
- `survey-results.xlsx` containing hashed IDs of survey participant
- `wikipedia-timezone-aliases-2018-04-28.csv` for local time estimates

## TO DO: 

- [ ] Calculate remaining rolling stats for sleep and LBGI/HBGI analysis
