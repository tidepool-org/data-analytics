# estimate-local-time.py
Python code for estimating the local time.

### dependencies:
* set up tidepool-data-env (see /data-analytics/readme.md)
* requires wikipedia-timezone-aliases-2018-04-28.csv (in github repository)

### TODO:
- [ ] write a function that compares whether two time zones are equivalent on a given day
- [ ] apply a clock drift correction
- [ ] there are cases where the time zone offset is an increment of 15, 30, or 45, but that amount of time zone offset does not exist for the given time zone
- [ ] unit tests
- [ ] assess the accuracy of the estimates

## the goal of the algorithm
The goal of the algorithm is to estimate the local time for each data point in each user's dataset. However, in order to estimate the local time, we need to know the time zone (TZ) that the user was in when each data point was collected, so we can convert UTC time to the local time. Given that all data that is ingested into the [Tidepool data model](http://developer.tidepool.org/data-model/) has a UTC time, the goal of the estimate-local-time algorithm is to estimate the time zone (TZ), so we can infer the time zone offset (TZO) and convert UTC time to the local time:

```
localTime = utcTime + timezoneOffset
```

### overview
Please note that the estimate-local-time algorithm is still in beta. This document reflects the logic used in version 0.0.3 of the algorithm. The general approach is to estimate the most likely TZ the Tidepool user was in on a given day, and for each day spanning their entire dataset. We found that estimating the TZ on a given day was a more tractable problem than trying to estimate the TZ the user was in for each second, minute, or hour on a given day.

There are three different approaches or methods that we use to estimate the TZ and TZO, which are explained in more detail in the logic section:

1. Use the TZ associated with upload records, to estimate the TZ and TZO

2. Use the device TZO, which is estimated by the bootstrapping-to-utc [(BtUTC)](http://developer.tidepool.org/chrome-uploader/docs/BootstrappingToUTC.html) algorithm to estimate the TZO

3. Impute (AKA infer) the TZ and TZO using the results from methods 1 and 2

### assumptions, caveats, and notes
* trying to estimate the TZ and TZO for each data point in datasets with millions of data points  that are generated from different diabetes devices -- all of which keep track of time in different ways -- is a very challenging problem. Though, this problem really should not exist in our modern, connected, flattened, internet-of-things world.
* we assume that the BtUTC algorithm is able to accurately estimate the UTC time from the device's time. We know this is not 100% true, as there are edge cases and pitfalls documeneted in the [BtUTC documentation](http://developer.tidepool.org/chrome-uploader/docs/BootstrappingToUTC.html).
* even though we estimate the TZO for each day, we do account for the exact time changes to and from daylight savings time (DST) occur. 
* for user’s using the Tidepool uploader, we assume that the user has selected the correct time zone, and that their device is set to the correct local time. 
* the BtUTC algorithm estimates clock drift, but does not correct for the clock drift.  
* we only make local time estimates on donated datasets, where the user has opted
in to share their data.

### logic
#### 1. UPLOAD METHOD: Use upload records to estimate the TZ and TZO

We heavily rely on the user's upload records to estimate the TZ the user was in for each day we have data for that user. If there are upload record(s) on a given day, we assign the most frequent TZ to that day. Then, once we know the TZ, we can look up the TZO for that day. By design, this logic favors uploads that occur multiple times per day (i.e., via Healthkit). In general, uploads can come from the Tidepool uploader, Tidepool Mobile via Healthkit, or through device manufacturer's APIs, which are linked to the Tidepool accounts.

Upload records are ideal as they typically capture the user's TZ at the time of upload. Data that comes through Tidepool Mobile via Healthkit is the "best" data to use for estimating the TZ, for two reasons:

* the upload records get the TZ from the mobile device and 

* uploads occur frequently, often several times per day. 

Uploads that are initiated through the Tidepool uploader, are also good, but not as good as uploads through Tidepool Mobile via Healthkit as they are subject to user errors. That is, the user must select the TZ and is responsible for making sure their device has the correct local time at upload. However, as of April 2018, the Tidepool Uploader now checks the device time at the time of upload and suggests that the user corrects the time on their device, if the local time and device time is off by more than 15 minutes, before they upload their device. 

Lastly, uploads can come into Tidepool through device manufacturer’s APIs. Because each API differs, we won’t address using those records here, besides mentioning that we do not use questionable upload data in the estimate-local-time algorithm. 

#### 2. DEVICE METHOD: Use the pump or cgm TZO, which is estimated by the BtUTC algorithm to estimate the TZO for a day when no uploads occurred

For days when no data was uploaded, we estimate the TZO using the pump and non-healthkit cgm TZO, which is estimated with the BtUTC algorithm. In the case that we have a TZO from both a pump and non-healthkit cgm and they have the same TZO, we can use either to estimate the TZO. If they disagree, however, we mark the local time estimate for that day as UNCERTAIN.

##### 2A. Infer TZ from upload records

If we are able to estimate the TZO for a given day using the pump and/or cgm TZO estimate, we then try to infer the TZ by comparing the estimated TZO to the upload TZOs. There are two different approaches we use (see 2A in the code):

* First, we compare the estimated TZO to interpolated upload records. We construct an interpolated time-series (referred to as a day-series in the code) that calculates the TZO for each day between uploads for each pump and cgm in the dataset. If the estimated TZO on a given day matches one of the day-series TZO for that day, we use the TZ associated with the day-series TZO for that day.

* If the TZO does not a match one of the day-series TZOs (i.e., the interpolated upload records), then we compare the estimated TZO to the TZO of the user’s home TZ. Here we define the home TZ as the TZ that the user most frequently uploads from. We have found that over 97% of our donated datasets have one TZ where the majority of downloads come from. If the estimated TZO on a given day matches the user’s home TZO for that day, we use the TZ associated with the home TZ for that day.

##### 2B. Infer TZ from previous day’s TZ

If we are able to estimate the TZO for a given day using the pump and/or cgm TZO estimate, and we are not able to infer the TZ using 2A, then see if the TZ can be inferred from the previous day's TZO. If the device TZO is equal to the previous day's TZO, AND if the previous day has a TZ estimate, then use the previous day's TZ estimate for the current day's TZ estimate.

#### 3. IMPUTE METHOD: Impute (AKA infer) the TZ and TZO using the results from methods 1 and 2

After making TZO and TZ estimates using methods 1 and 2, we see if we can impute (AKA infer or interpolate) the TZ and TZO on days when we do not have upload records and do not have reliable pump or cgm TZO estimates. We assess each gap separately, where a gap is defined as having consecutive days with no TZO estimate. Here is the logic associated with each gap:
* First we see if the day before and after the gap have the same TZ. If they do, we assign each day in the gap with that TZ. We then infer the TZO using the TZ for each gap day, which ensures that we properly account for DST changes.
* If the day before and after the gap do not have a TZ estimate, we then see if their TZOs are the same. If they are, we assign that TZO to each day in the gap.
* Lastly, if the day before and after the gap do not have the same TZ or TZO, we mark every day in the gap as UNCERTAIN  and we annotate that we are not able to impute the TZO.

For this method, we also keep track of the size of the gap, as we have good confidence in the estimate if the gap size is small, and less confidence in the estimate if the gap size is large. For example, if `gapSize = 1 day`, then it tell us that we had an estimate of the TZO (with the `UPLOAD` or `DEVICE` method) on the day before and day after the missing day. In that case (`gapSize = 1`) we can be pretty confident that the person was in the same time zone. On the flip side, if `gapSize = 100 days`, it is less likely that the person was in the same TZ over the course of 100 days. 

In regards to the `IMPUTE` method, as the gap size increases, our confidence in the TZO and local time estimate decreases. It should also be noted that defining a gap size threshold of when we can have confidence in the `IMPUTE` method is an area of future research. In the meantime, we have decided not to draw such a threshold. Rather, we provide the gap size and leave it up to the analyst to define a threshold that makes the most sense for the analysis they are conducting.

### data fields
When you look at datasets that include a local time estimate, you will find the following fields:

* _est.localTime_: "2016-11-06 13:00:50”,
* _est.type_: "DEVICE”,
* _est.timezone_: "America/Los_Angeles”,
* _est.timezoneOffset_: -480,
* _est.timeProcessing_: "utc-bootstrapping",
* _est.annotations_: "likely-travel",
* _est.gapSize_: null,
* _est.version_: 0.0.3

These new fields, which are not in our data model, all begin with "est", as these are our best estimate of the local time. Here are the definitions of the new fields:

* _est.localTime_: the local time estimate 

```
est.localTime = time + est.timezoneOffset
```

* _est.type_: there are four different estimate types that we assign to each data point in the dataset.

```
[UPLOAD, DEVICE, IMPUTE, or UNCERTAIN]
```

With exception to `UNCERTAIN`, the estimation type refers to estimation method we use to 
estimate the time zone offset, which is needed to estimate the local time.

* `UPLOAD`: this method uses upload records. Upload records are ideal as they include TZ and TZO information. In most cases, this is the best information we have to estimate the TZ, TZO, and local time.

* `DEVICE`: this method uses pump and non-healthkit cgm TZO information, which is estimated with Tidepool’s BtUTC algorithm at the time the data is uploaded into the Tidepool database.

* `IMPUTE`: this method infers or interpolates the TZO (and TZ if possible), using the TZ and TZO information on the before and after the gap. 

* `UNCERTAIN`: there were cases where we were not able to estimate the TZO and local time. 

* _est.timezone_: the estimated TZ that the user was in when the data point was created by the user’s device.

* _est.timezoneOffset_: the TZO from UTC time in minutes.

* _est.timeProcessing_: this field refers to the type of BtUTC procedure associated with the point that was used to estimate the time zone. See the BtUTC documentation for details.

* _est.annotations_: we put notes in this field to help explain how the estimates were made (e.g., "tz-inferred-from-pump.upload.imputed” means that we inferred the TZ using pump upload data).

* _est.gapSize_: this field is only used with the _est.type_ = `IMPUTE`. It indicates the number of consecutive days missing a TZO estimate (i.e., a gap in estimated TZO data) that were filled using the `IMPUTE` method. 

