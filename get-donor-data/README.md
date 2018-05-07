# get-donor-data

Python code for getting a current list of donors, and for pulling
their json files.

Here are the main functions:
* get-donor-list.py
* get-donor-json-files.py
* flatten-json-to-csvs.py
* anonymized-export.py

## dependencies:
* set up get-donor-data virtual environment (see /data-analytics/readme.md)
* requires that donors are accepted (currently a manual process)
* requires a list of qa accounts on production to be ignored
* requires environmental variables: import environmentalVariables.py
* requires https://github.com/tidepool-org/command-line-data-tools
* anonymized-export requires:
    * Tidepool json data (e.g., PHI-jill-jellyfish.json)
    * commandline tool 'jq' for making a pretty json file

## TODO:
- [X] waiting for QA to cross reference donor accounts with testing accounts,
once they do, then the ignoreAccounts file needs to be updated
- [ ] flatten-json-to-csvs.py has some parts of code that need to be removed 
- [ ] once the process of accepting new donors is automated, the use of the
dateStamp will make more sense. As it is being used now, it is possible that
the dateStamp does NOT reflect all of the recent donors.
- [ ] move this entire process to the cloud
- [ ] move code that is used by multiple scripts to a utility folder/library
- [ ] make sure that jq library is added to the virtual environment
- [ ] pull in jill-jellyfish.json dataset from AWS if no file is given
