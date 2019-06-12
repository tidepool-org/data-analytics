# get-donor-data

This is the first step in the Big Data Processing Pipeline.

Here are the list of python files and their usage:

- accept_new_donors_and_get_donor_list.py* 
  - This is a standalone script which accepts new donors into Tidepool's Big Data Donation Project and returns a .csv list of unique user IDs.
- get_single_donor_metadata.py
  - Returns the metadata for a single Tidepool account
  - Can be used as a standalone script (saves an external .csv) or as an imported module `get_shared_metadata()`
- get_single_tidepool_dataset.py
  - Returns the data within a single Tidepool account
  - Can be used as a standalone script (saves an external .csv) or as an imported module `get_data()`
- get_all_donor_data_batch_process.py
  - This is a wrapper script for all the above files. It accepts all bigdata donation project donors, and then pulls of their datasets for further processing.
- example_get_all_data_for_single_user.py*
  - This is an example file that uses `get_shared_metadata()` and `get_data()` as modules to retrieve metadata and account data within memory.

## dependencies:
* All files are run within a tidepool-analytics virtual environment (see /data-analytics/readme.md)
* *requires a big data environmental file with: import environmentalVariables.py

## TODO:
- [ ] Remove deprecated code
