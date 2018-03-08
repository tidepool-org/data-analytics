# get-donor-data

Python code for getting a current list of donors, and for pulling
their json files.

There are three main functions:
* get-donor-list.py
* get-donor-json-files.py
* flatten-json-to-csvs.py

## dependencies:
* requires that donors are accepted (currently a manual process)
* requires a list of qa accounts on production to be ignored
* requires environmental variables: import environmentalVariables.py
* requires https://github.com/tidepool-org/command-line-data-tools

## TODO:
- [X] waiting for QA to cross reference donor accounts with testing accounts,
once they do, then the ignoreAccounts file needs to be updated
- [ ] flatten-json-to-csvs.py has some parts of code that need to be removed 
- [ ] once the process of accepting new donors is automated, the use of the
dateStamp will make more sense. As it is being used now, it is possible that
the dateStamp does NOT reflect all of the recent donors.
- [ ] move this entire process to the cloud
