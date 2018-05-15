# local-time-estimate.py
Python code for estimating the local time.


### dependencies:
* set up tidepool-data-env (see /data-analytics/readme.md)
* requires wikipediaDeprecatedTimezonesAliases2018_04_28.csv

### TODO:
- [] write a function that compares whether two timezones are
equivalent on a given day
- [] current version does not account for cases where pump and cgm
device tzo are different, which may be indicative of a larger problem with the
underlying data
- [] apply a clock drift correction
- [] unit tests

## local-time-estimate algorithm

### overview
This algorithm is still in beta.

### logic


### data fields
When you look at datasets, that include a local time estimate, you will find the following fields:

* _est.localTime_: "2016-11-06 13:00:50”,
* _est.type_: "DEVICE”,
* _est.timezone_: "America/Los_Angeles”,
* _est.timezoneOffset_: -480,
* _est.timeProcessing_: "utc-bootstrapping",
* _est.annotations_: "tz-inferred-from-pump.upload.imputed",
* _est.gapSize_: null,
* _est.version_: 0.0.2

These new fields, which are not in our data model, all begin with "est",
as these are our best estimate of the local time. Here are the definitions of the
new fields:
* _est.localTime_: the local time estimate. 
```
est.localTime = time + est.timezoneOffset
```
* _est.type_: there are four different estimate types that we assign to each data point in the dataset.
```
[UPLOAD, DEVICE, IMPUTE, or UNCERTAIN]
```
With exception to `UNCERTAIN`, the estimation type refers to estimatation method we use to 
estimate the time zone offset, which is needed to estimate the local time.
    * `UPLOAD`: this method uses upload records. Upload records are ideal as they include time zone and
    time zone offset information. In most cases, this is the best information we have to estimate the 
    time zone, time zone offset, and local time.
    * `DEVICE`: this method uses pump and non-healthkit cgm time zone offset information, which was 
    estimated with Tidepool’s  bootstrapping-to-utc procedure.
    * `IMPUTE`: this method infers or interpolates the time zone offset between adjacent data points 
    in the dataset.
    * `UNCERTAIN`: there were cases where we were not able to estimate the time zone offset and local 
    time. NOTE: these UNCERTAIN data points were removed from the datasets before re-qualification.
* _est.timezone_: the estimated time zone that the user was in when the data point was created by the 
user’s device.
* _est.timezoneOffset_: the time zone offset from UTC time in minutes.
* _est.timeProcessing_: this field refers to the type of utc-bootstrapping procedure associated with 
the point that was used to estimate the time zone.
* _est.annotations_: we put notes in this field to help explain how the estimates were made (e.g., 
"tz-inferred-from-pump.upload.imputed” means that we inferred the time zone (tz) using pump upload data).
* _est.gapSize_: this field is only used with the _est.type_ = `IMPUTE`. It indicates the number of missing 
days in a row (i.e., a gap in time zone offset data) that were filled using the `IMPUTE` method. For example,
if `gapSize = 1`, then it tell us that we had an estimate of the time zone offset (with the `UPLOAD` or 
`DEVICE` method) on the day before and day after the missing day. In that case (`gapSize = 1`) we can be 
pretty confident that the person was in the same time zone. On the flip side, as the gapSize increases,
our confidence in the time zone offset and local time estimate decreases.
