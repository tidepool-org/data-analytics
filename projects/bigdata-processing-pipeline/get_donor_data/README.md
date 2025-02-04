# get-donor-data

This is the first step in the Tidepool Big Data Donation Project (TBDDP) Processing Pipeline.

NOTE: if you are a Tidepool employee processing TBDDP data, or you have a study with lots of shared accounts, you only need to run get_all_donor_data_batch_process.py as it will accept all new donors (users) AND will get all metadata and datasets.

Here are the list of python files and their usage:

- **accept_new_donors_and_get_donor_list.py***
  - This is a standalone script which accepts pending donors into Tidepool's Big Data Donation Project and returns a .csv list of unique user IDs.
- **get_single_donor_metadata.py**
  - Returns the metadata for a single Tidepool account
  - This file can be used as a standalone script (saves an external .csv) or as an imported module `get_shared_metadata()`
- **get_single_tidepool_dataset.py**
  - Returns the data within a single Tidepool account
  - This file can be used as a standalone script (saves an external .csv) or as an imported module `get_data()`
- **get_all_donor_data_batch_process.py**
  - This is a standalone wrapper script for all the above files. It accepts all bigdata donation project donors, and then pulls of their datasets for further processing.
- **example_get_all_data_for_single_user.py***
  - This is an example file that uses `get_shared_metadata()` and `get_data()` as modules to retrieve metadata and account data within memory.

## dependencies:
* All files are run within a conda virtual environment (see /data-analytics/readme.md) named, `tbddp` which can be loaded from the environment.yml file
* requires a big data environmental file with: import environmentalVariables.py

