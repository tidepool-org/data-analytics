# qualify-data

Python code for qualifying donated data

There is one main functions:
* qualify.py

## dependencies:
* requires that data is in the format output from the get-donor-data tools
* requires a json file with qualifying criteria

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
