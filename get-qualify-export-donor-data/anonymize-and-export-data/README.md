# anonymize-and-export
Python code for anonymizing and exporting donated data

There is one main functions:
* anonymize-and-export.py

## dependencies:
* set up tidepool-analytics virtual environment (see /data-analytics/readme.md)
* requires Tidepool data (e.g., PHI-jill-jellyfish.json)
* requires commandline tool 'jq' for making the pretty json file

## TODO:
- [ ] break script into separate load, filter, clean, anonymize, and export funtions
- [ ] the format of the xlsx files could/should be improved
