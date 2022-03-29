# anonymize-and-export
Python code for anonymizing and exporting donated diabetes data

There is one main function:
* [anonymize-and-export.py](./anonymize-and-export.py)

## Process Pseudocode

For each data sample in a user’s dataset:

1. Remove manufacturer identifying names from the following annotation fields:
    * `annotations.code`
    * `suppressed.annotations.code`
    * `suppressed.suppressed.annotations.code`
2. For each field listed in [dataFieldExportList.csv](example-data/dataFieldExportList.csv) where the `hashNeeded` column value is `TRUE`, replace its value with the following hash value:
    > `substring(hexstring(sha256(value + salt + userId)), 0, 8)`
3. For each user-provided schedule name in the fields `basalSchedules`, `bgTargets`, `carbRatios`, `insulinSensitivities`, replace its name with the following hash value:
    > `substring(hexstring(sha256(name + salt + userId)), 0, 8)`
4. Apply the following hash function to the user ID:
    > `hexstring(sha256(userId + salt))`

where the pseudo-code elements are:

* `salt` is a random value provided as an input parameter to the script. This makes the anonymized values more resilient against [rainbow table](https://en.wikipedia.org/wiki/Rainbow_table) attacks.
* `userId` is the Tidepool user ID of the user whose data is being anonymized. It is either a 10-digit hexadecimal value (v1), or a 32-digit hexadecimal value (v2).
* `sha256` is the [SHA-256](https://en.wikipedia.org/wiki/SHA-2) algorithm that computes a 256-bit hash value from its input data.
* `hexstring` converts its input value to a string of hexadecimal digits.
* `substring` returns a subset of a string from a `start` index up to `length` characters.

## Dependencies

* set up tidepool-analytics virtual environment (see /data-analytics/readme.md)
* requires Tidepool data (e.g., PHI-jill-jellyfish.json)
* requires commandline tool 'jq' for making the pretty json file

## TODO

- [ ] break script into separate load, filter, clean, anonymize, and export funtions
- [ ] the format of the xlsx files could/should be improved
