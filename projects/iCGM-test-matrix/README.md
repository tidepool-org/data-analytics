# iCGM Test Matrix

This project finds snapshots of data to explore the sensitivity of the Loop Algorithm over the entire range of BG values. Each snapshot is a 48-hour window of data. In the center of this data is an "evaluation point" which falls into one of the 9 conditions detailed in the table below.

The primary goal of this project is to find 9 snapshots for each condition from 100 datasets in the Tidepool Big Data Donation Project for a total of 900 snapshots and export them for simulator use.

The secondary goal is to calculate the distribution of all 9 conditions within the entire TBDDP donor population.

## Scripts

There are 3 python scripts used in this project:

- **icgm_condition_finder.py** - Given a Tidepool donor dataset, returns 9 locations (if available) of each condition along with some other statistics (see [Condition Finder Output][#condition-finder-ouput] below)
- **batch-icgm-condition-stats.py** - A batch script wrapper for the icgm_condition_finder. Given a folder of Tidepool datasets, creates a .csv output of condition locations and stats for every file.
- **snapshot_processor.py** - Given the output of batch-icgm-condition-stats.py, takes each 48-hour snapshot location for every dataset and converts it into a set of dataframes to be used by the pyLoopKit simulator. (Exports to a 10-element tuple pickle file)

## Condition Table

There are 3 value conditions and 3 rate of change conditions with a combined 9 unique iCGM states that any iCGM data point can exist within as shown in the table below.

<table>
    <tbody>
      	<tr>
          <td></td>
          <td></td>
          <td colspan=3><b>Median BG value of the previous 6 BG values<br>(mg/dL)</b></td>
        </tr>
        <tr>
            <td></td>
            <td></td>
            <td>[40-70)</td>
          	<td>[70-180]</td>
          	<td>(180-400]</td>
        </tr>
        <tr>
          <td rowspan=3><b>Rate of change of the<br>previous 3 BG values <br>(mg/dL/min)</b></td>
          	<td>< -1</td>
          	<td>[40-70) <br>&<br> < -1 </td>
          	<td>[70-180] <br>&<br> < -1 </td>
            <td>(180-400] <br>&<br> < -1 </td>
        </tr>
        <tr>
            <td>[-1 to 1]</td>
          	<td>[40-70) <br>&<br> [-1 to 1]</td>
          	<td>[70-180] <br>&<br> [-1 to 1]</td>
            <td>(180-400] <br>&<br> [-1 to 1]</td>
        </tr>
        <tr>
            <td>> 1</td>
          	<td>[40-70) <br>&<br> > 1</td>
          	<td>[70-180] <br>&<br> > 1</td>
            <td>(180-400] <br>&<br> > 1</td>
        </tr>
    </tbody>
</table>

The conditions are numbered 1-9 as follows:

| Condition # | 30min Median BG (mg/dL) <br />& <br />15min Rate of Change (mg/dL/min) |
| :---------: | :----------------------------------------------------------- |
|      1      | [40-70) & < -1                                               |
|      2      | [70-180] & < -1                                              |
|      3      | (180-400] & < -1                                             |
|      4      | [40-70) & [-1 to 1]                                          |
|      5      | [70-180] & [-1 to 1]                                         |
|      6      | (180-400] & [-1 to 1]                                        |
|      7      | [40-70) & > 1                                                |
|      8      | [70-180] & > 1                                               |
|      9      | (180-400] & > 1                                              |

## Condition Finder Algorithm

The algorithm for finding a snapshot is as follows

- Fit the CGM trace to a 5-minute time series to uncover gaps
- Calculate the median mg/dL value with a 30-minute (6 cgm points) rolling window 
- Calculate the slope in mg/dL/min with a 15-minute (3 cgm points) rolling window
- Apply one of the 9 conditions labels to each CGM point
- Calculate the max gap size of the cgm trace in a 48 hour *centered* rolling window (where the evaluation point is in the center)
- Randomly select one evaluation point for each condition that does not overlap with any other 48-hour snapshot and has a max gap <= 15 minutes

## Condition Finder Output

The output for the icgm_condition_finder.py and batch processing script are:

- **file_name** - The file name of the .csv analyzed
- **nRoundedTimeDuplicatesRemoved** - The number of cgm duplicates removed after rounding to the nearest 5 minutes
- **cgmPercentDuplicated** - Percent of the cgm data that was duplicated
- **gte40_lt70** - The number of cgm entries with a median BG value of the previous 6 BG values (mg/dL) in the range [40, 70) (mg/dL) 
- **gte70_lte180** - The number of cgm entries with a median BG value of the previous 6 BG values in the range [70, 180] (mg/dL) 
- **gt180_lte400** - The number of cgm entries with a median BG value of the previous 6 BG values in the range (180, 400] (mg/dL) 
- **lt-1** - The number of cgm entries with a rate of change of the previous 3 BG values less than -1 (mg/dL/min)
- **gte-1_lte1**- The number of cgm entries with a rate of change of the previous 3 BG values in the range [-1, 1] (mg/dL/min)
- **gt1** - The number of cgm entries with a rate of change of the previous 3 BG values greater than 1 (mg/dL/min)
- **cond[0-9]** - The number of total evaluation points that match a given condition (note that cond0 are the number of cgm entries that could not be evaluated under a condition due to a lack of data)
- **cond[1-9]_eval_loc** - The id location of a randomly sampled evaluation point
- **status** - The batch processing completion status of each file