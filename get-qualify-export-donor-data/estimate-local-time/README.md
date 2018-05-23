# estimate-local-time.py
Python code for estimating the local time.


### dependencies:
* set up tidepool-data-env (see /data-analytics/readme.md)
* requires wikipedia-timezone-aliases-2018-04-28.csv (in github repository)

### TODO:
- [ ] write a function that compares whether two time zones are
equivalent on a given day
- [ ] apply a clock drift correction
- [ ] there are cases where the time zone offset is an increment of 15, 30, or 
45, but that amount of time zone offset does not exist for the given time zone
- [ ] unit tests
- [ ] assess the accuracy of the estimates

## the algorithm
The goal of the algorithm is to estimate the local time for each data point in
user's dataset. However and given that all Tidepool data has an estimate of the UTC
time, our real goal is to estimate the time zone (TZ) and time zone offset (TZO), so
we can convert UTC time to the local time.  

### overview
The estimate-local-time algorithm is still in beta. This document reflects the 
logic in version 0.0.3 of the algorithm. The general approach is to estimate
the most likely TZ the Tidepool user was in on a given day, spanning the
entire date range of their data. We found that estimating the TZ on a 
given day was more tractable problem than trying to estimate the TZ the 
user was in for each second, minute, or hour on a given day.

There are three different approaches or methods that we use to estimate the 
TZ and TZO, which are explained in more detail in the logic section:

1. Use upload records to estimate the TZ and TZO
2. Use device TZO to estimate the TZO
3. Impute (AKA infer) the TZ and TZO using the results from methods 1 and 2

After util

### assumptions, caveats, and notes
* trying to estimate the TZ and TZO for each data point in a dataset that can
take millions of data points from diabetes devices that keep track of time in 
different ways is a very challenging problem. Though, this problem really should
not exist in our modern, connected, "flattened", internet of things world.
* we assume that the bootstrapping-to-utc algorithm is able to accurately
estimate the UTC time from the device's time. We know this is not 100% true,
as many of the edge cases and pitfalls are documeneted in the [BtUTC documentation] (http://developer.tidepool.org/chrome-uploader/docs/BootstrappingToUTC.html).
* we only make local time estimates using donated datasets, where the user has opted
in to share their data.
* 

### logic
We heavily rely on the user's upload records to estimate the time zone that the 
user was in on each day. Uploads can come from the Tidepool uploader, Tidepool 
Mobile via Healthkit, or through device manufacturer's APIs, which are linked to
the Tidepooler's account.

### data fields
When you look at datasets, that include a local time estimate, you will find the following fields:

* _est.localTime_: "2016-11-06 13:00:50”,
* _est.type_: "DEVICE”,
* _est.timezone_: "America/Los_Angeles”,
* _est.timezoneOffset_: -480,
* _est.timeProcessing_: "utc-bootstrapping",
* _est.annotations_: "tz-inferred-from-pump.upload.imputed",
* _est.gapSize_: null,
* _est.version_: 0.0.3

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
