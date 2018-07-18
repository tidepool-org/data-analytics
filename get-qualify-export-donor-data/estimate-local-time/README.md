# estimate-local-time.py
A python algorithm for estimating the local time

### Dependencies:
* set up tidepool-analytics virtual environment (see /data-analytics/readme.md)
* Requires wikipedia-timezone-aliases-2018-04-28.csv (in github repository)

## Why?
So, why bother with estimating the local time? Well, knowing the local time of each diabetes device data point is required for those of us that are interested in doing time of day analyses (e.g., what is average lunchtime postprandial blood glucose level for 13 year olds?).

In an ideal world, every diabetes device would keep track of the time zone (TZ) and UTC time. Unfortunately, each diabetes device keeps track of time differently. Most devices only keep a device time, which relies on the user for updates such as travel across time zones, daylight savings, and clock drift corrections. These devices typically have no notion of the TZ or UTC time. There are also cases where we are provided the UTC time, but there is no indication of the local time (e.g., data that comes through Tidepool Mobile via Healthkit). 

We’ve also found the the user maintenance is subject to human error. For instance, a user may forget to update their device time for daylight savings for 4 months. Fortunately, this use case is easy to detect and retroactively correct, which we do using Tidepool's bootstrapping to UTC algorithm [BtUTC](http://developer.tidepool.org/chrome-uploader/docs/BootstrappingToUTC.html).

The other good news is that data ingested into the [Tidepool data model](http://developer.tidepool.org/data-model/) either has a UTC time, or is assigned one upon ingestion. With few exceptions, this means that data from pump and cgm devices can be aligned. And, assuming we can estimate the TZ the user was in when the data was captured, a local time can be estimated, which is the goal of this algorithm. Please note that the current exceptions to data types that have accurate UTC times include blood glucose meter data and pumps that do not capture time change events. 

## Goal of the algorithm
The goal of the algorithm is to estimate the local time for each data point in each user's dataset. Given that most Tidepool data has a UTC time, the real goal is to estimate the TZ, so we can infer the time zone offset (TZO), which can then be used to convert UTC time to the local time. 

Our approach to the problem of estimating the TZO for each data point, is to first estimate the TZO for each day in a user’s dataset, and if possible, to estimate the TZ the person was in for the majority of that day. Once we have an estimate of the likely TZO for each day in a user’s dataset, we then apply these TZOs to the UTC time to estimate the local time of each data point:

```
localTime = utcTime + timezoneOffset
```

### Overview
Please note that the estimate-local-time algorithm is still in beta. This document reflects the logic used in version 0.0.3 of the algorithm. The general approach is to estimate the most likely TZ the Tidepool user was in on a given day, and for each day spanning their entire dataset. We found that estimating the TZ on a given day was a more tractable problem than trying to estimate the TZ the user was in for each second, minute, or hour on a given day. Also, we only use data from pump and cgm devices and upload records to make the local time estimate. 

There are four steps and three different approaches or methods that we use to estimate the TZ and TZO for each day, which are explained in more detail in the logic section:

1. Use the TZ associated with upload records, to estimate the TZ and TZO for a given day

2. Use the device TZO, which is estimated by the [BtUTC](http://developer.tidepool.org/chrome-uploader/docs/BootstrappingToUTC.html) algorithm to estimate the TZO

3. Impute (AKA infer) the TZ and TZO using the results from methods 1 and 2

4. Estimate local time for each data point

### Assumptions, caveats, and notes
* Trying to estimate the TZ and TZO for each data point in datasets with millions of data points  that are generated from different diabetes devices — all of which keep track of time in different ways — is a very challenging problem. And at the same point, it is a little disappointing that we have to solve this problem in our modern, connected, flattened, internet-of-things world.

* We assume that the BtUTC algorithm is able to accurately estimate the UTC time from the device's time. We know this is not 100% true, as there are edge cases and pitfalls documented in the [BtUTC documentation](http://developer.tidepool.org/chrome-uploader/docs/BootstrappingToUTC.html).

* Blood glucose meters (i.e., the smbg data type) do not capture time change events, and therefore, the UTC time is highly suspect. For this version of the algorithm, we do not use blood glucose meter data in the algorithm; however, we do apply the algorithm to smbg data to get an estimated local time. Please use this data with caution as the time information is not as reliable as pump and cgm data. Also, if the device time does not equal the estimated local time, then the smbg data should not be used.

* We apply a bug fix to the BtUTC algorithm that is planned but not currently implemented in the Tidepool data model. Specifically, we correct large and unrealistic TZOs that come from the BtUTC algorithm. This bug fix subtracts 1440 minutes from TZOs greater than 840 and adds that offset to the conversion offset, and it also adds 1440 to TZOs less than -720 and subtracts that amount from the conversion offset. This procedure is repeated until the TZO is within the valid range of -720 to 840. 

* Please note that the TZO in the Tidepool data model is not a true TZO, and should not be used to convert UTC time to local time. The TZO in the data model is an offset used in addition to the conversion offset that the BtUTC algorithm uses to convert a device time to UTC time. Please see the BtUTC documentation for details.

* We are aware of and are working on a bug in the BtUTC algorithm where the UTC time is incorrect if the device time resets back to the factory default time. If you see a time change greater than 1 year in a dataset (i.e., the difference between data fields _change.to_ and _change.from_), the data that occurs prior to the large time correct may not be accurate.

* Even though we estimate the TZO at day resolution, we do account for the exact time changes to and from daylight savings time (DST) occur. Further, many users do not make DST changes (to/from) at the exact time or day of the DST change. If we know the TZ that the user was in, we are able to account for the exact time of the DST change.  

* On days when users travel to/from a different time zone, we capture the TZ that the user spent the majority of the day in. This implicitly means that the estimated local time on those days will be wrong for a small proportion of the day. We have, however, annotated when we think users are traveling in the est.annotations field.

* For users using the Tidepool uploader, we assume that the user has selected the correct time zone, and that their device is set to the correct local time. 

* For the impute method (see section 3 below), our confidence in the impute method decreases as the gap size increases.

* The BtUTC algorithm estimates clock drift, but does not correct for the clock drift.  

* We only make local time estimates on donated datasets, where the user has opted
in to share their data.

### Logic
#### 1. UPLOAD METHOD: Use upload records to estimate the TZ and TZO

We heavily rely on the user's upload records to estimate the TZ the user was in for each day we have data for that user. If there are upload record(s) on a given day, we assign the most frequent TZ to that day. Then, once we know the TZ, we can look up the TZO for that day. By design, this logic favors uploads that occur multiple times per day (i.e., via Healthkit). In general, uploads can come from the Tidepool uploader, Tidepool Mobile via Healthkit, or through device manufacturer's APIs, which are linked to Tidepool users'accounts.

Upload records are ideal as they typically capture the user's TZ at the time of upload. Data that comes through Tidepool Mobile via Healthkit is the "best" data to use for estimating the TZ, for two reasons:

* the upload records get the TZ from the mobile device and 

* uploads occur frequently, often several times per day. 

Uploads that are initiated through the Tidepool uploader, are also good, but not as good as uploads through Tidepool Mobile via Healthkit as they are subject to user errors. That is, the user must select their TZ and is responsible for making sure their device has the correct local time at upload. However, as of April 2018, the Tidepool Uploader now checks the device time at the time of upload and suggests that the user corrects the time on their device, if the local time and device time is off by more than 15 minutes, before they upload their device. 

Lastly, uploads can come into Tidepool through device manufacturer’s APIs. Because each API differs, we won’t address using those records here, besides mentioning that we do not use questionable upload data in the estimate-local-time algorithm. 

#### 2. DEVICE METHOD: Use the pump or cgm TZO, which is estimated by the BtUTC algorithm to estimate the TZO for a day when no uploads occurred

For days when no uploads occurred, we estimate the TZO using the pump and non-healthkit cgm TZO, which is estimated with the BtUTC algorithm. In the case that we have a TZO from both a pump and non-healthkit cgm and they have the same TZO, we can use either to estimate the TZO. If they disagree, however, we mark the local time estimate for that day as UNCERTAIN.

##### 2A. Infer TZ from upload records

If we are able to estimate the TZO for a given day using the pump and/or cgm TZO estimate, we then try to infer the TZ by comparing the estimated TZO to the upload TZOs. There are two different approaches we use (see 2A in the code):

* First, we compare the estimated TZO to imputed upload records. We construct an imputed time-series (referred to as a day-series in the code) that calculates the TZO for each day between uploads for each pump and cgm in the dataset. If the estimated TZO on a given day matches one of the day-series TZO for that day, we use the TZ associated with the day-series TZO for that day.

* If the TZO does not match one of the day-series TZOs (i.e., the imputed upload records), we then compare the estimated TZO to the TZO of the user’s home TZ. Here we define the home TZ as the TZ that the user most frequently uploads from. We have found that over 97% of our donated datasets have one TZ where the majority of downloads come from. If the estimated TZO on a given day matches the user’s home TZO for that day, we use the TZ associated with the home TZ for that day.

Please note that the imputed uploaded records (AKA day series) are only used to infer the TZ for a given day. This is important, because it means that if the imputed uploaded records are not accurate, which would be the case when someone travels in between uploads, we can still accurately estimate the TZO before, during, and after the travel if the pump or cgm captured the travel, as the TZO estimates are estimated from the pump and/or cgm data.

##### 2B. Infer TZ from previous day’s TZ

If we are able to estimate the TZO for a given day using the pump and/or cgm TZO estimate, and we are not able to infer the TZ using 2A, then we see if the TZ can be inferred from the previous day's TZO. If the device TZO is equal to the previous day's TZO, AND if the previous day has a TZ estimate, then use the previous day's TZ estimate for the current day's TZ estimate.

#### 3. IMPUTE METHOD: Impute (AKA infer) the TZ and TZO using the results from methods 1 and 2

After making TZO and TZ estimates using methods 1 and 2, we see if we can impute (AKA infer or interpolate) the TZ and TZO on days when we do not have upload records and do not have reliable pump or cgm TZO estimates. We assess each gap separately, where a gap is defined as having consecutive days with no TZO estimate. Here is the logic associated with each gap:
* First we see if the day before and after the gap have the same TZ. If they do, we assign each day in the gap with that TZ. We then infer the TZO using the TZ for each gap day, which ensures that we properly account for DST changes.
* If the day before and after the gap do not have a TZ estimate, we then see if their TZOs are the same. If they are, we assign that TZO to each day in the gap, and do NOT make an estimate of the TZ.
* Lastly, if the day before and after the gap do not have the same TZ or TZO, we mark every day in the gap as UNCERTAIN and we annotate that we are not able to impute the TZO.

For this method, we also keep track of the size of the gap, as we have good confidence in the estimate if the gap size is small, and less confidence in the estimate if the gap size is large. For example, if `gapSize = 1 day`, then it tell us that we had an estimate of the TZO (with the `UPLOAD` or `DEVICE` method) on the day before and day after the missing day. In that case (`gapSize = 1`) we can be pretty confident that the person was in the same time zone. On the flip side, if `gapSize = 100 days`, it is less likely that the person was in the same TZ over the course of 100 days. 

In regards to the `IMPUTE` method, as the gap size increases, our confidence in the TZO and local time estimate decreases. It should also be noted that defining a gap size threshold of when we can have confidence in the `IMPUTE` method is an area of future research. In the meantime, we have decided not to draw such a threshold. Rather, we provide the gap size and leave it up to the analyst to define a threshold that makes the most sense for the analysis they are conducting.

#### 4. Estimate local time for each data point
Lastly, once we have made our best estimate of the TZO for each day in a user’s dataset, we then apply the estimated TZO to each data point in the dataset, and then convert the UTC time to the local time.

### data fields
When you look at datasets that include a local time estimate, you will find the following fields:

* _est.localTime_: "2016-11-06 13:00:50”,
* _est.type_: "DEVICE”,
* _est.timezone_: "America/Los_Angeles”,
* _est.timezoneOffset_: -480,
* _est.timeProcessing_: "utc-bootstrapping",
* _est.annotations_: "tz-inferred-from-pump.upload.imputed",
* _est.gapSize_: null,
* _est.version_: “v0.0.3”

These new fields, which are not in our data model, all begin with "est", as these are our best estimate of the local time. Here are the definitions of the new fields:

* _est.localTime_: the local time estimate 

```
est.localTime = time + est.timezoneOffset
```

* _est.type_: there are four different estimate types that we assign to each data point in the dataset: [`UPLOAD`, `DEVICE`, `IMPUTE`, or `UNCERTAIN`]. With exception to `UNCERTAIN`, the estimation type refers to estimation method we use to estimate the time zone offset, which is needed to estimate the local time.

 * `UPLOAD`: this method uses upload records. Upload records are ideal as they include TZ and TZO information. In most cases, this is the best information we have to estimate the TZ, TZO, and local time.

 * `DEVICE`: this method uses pump and non-healthkit cgm TZO information, which is estimated with Tidepool’s BtUTC algorithm at the time the data is uploaded into the Tidepool database.

 * `IMPUTE`: this method infers or interpolates the TZO (and TZ if possible), using the TZ and TZO information on the before and after the gap. 

 * `UNCERTAIN`: there were cases where we were not able to estimate the TZO and local time. 

* _est.timezone_: the estimated TZ that the user was in when the data point was created by the user’s device.

* _est.timezoneOffset_: the TZO from UTC time in minutes.

* _est.timeProcessing_: this field refers to the type of BtUTC procedure associated with the point that was used to estimate the time zone. See the BtUTC documentation for details.

* _est.annotations_: we put notes in this field to help explain how the estimates were made (e.g., "tz-inferred-from-pump.upload.imputed” means that we inferred the TZ using pump upload data).

* _est.gapSize_: this field is only used with the _est.type_ = `IMPUTE`. It indicates the number of consecutive days missing a TZO estimate (i.e., a gap in estimated TZO data) that were filled using the `IMPUTE` method. 

### TODO:
- [ ] Write a function that compares whether two time zones are equivalent on a given day
- [ ] The algorithm currently uses the previous days TZ to infer the current days TZ, but can be improved
if the the algorithm looks at the next days TZ offset as well.
- [ ] Put est.localTime in ISO format
- [ ] Change format of the version number
- [ ] Change est.timezone name to est.timeZone 
- [ ] Resolve cases where the time zone offset is an increment of 15, 30, or 45, but that amount of time zone offset does not exist for the given time zone
- [ ] Mark smbg local time estimates as UNCERTAIN if the time zone offset does not match the the estimated time zone offset
- [ ] Apply fix to the factory reset time bug (see the assumptions, caveats, and notes section above)
- [ ] Unit tests
- [ ] Assess the accuracy of the local time estimates
