# iCGM Test Matrix

This project finds snapshots of data to explore the sensitivity of the Loop Algorithm over the entire range of BG values. Each snapshot is a 48-hour window of data. In the center of this data is an "evaluation point" which falls into one of the 9 conditions detailed in the table below.

The primary goal of this project is to find 9 snapshots for each condition from 100 datasets in the Tidepool Big Data Donation Project for a total of 900 snapshots.

The secondary goal is to calculate the distribution of all 9 conditions within the entire TBDDP donor population.

## Condition Table

There are 3 value conditions and 3 rate of change conditions with a combined 9 unique iCGM states that any iCGM data point can exist within as shown in the table below.

<table>
    <tbody>
      	<tr>
          <td></td>
          <td></td>
          <td colspan=3><b>Median BG value of the previous 6 BG values<br>(mg/dL)</b></td>
        </tr>
        <tr>
            <td></td>
            <td></td>
            <td>[40-70)</td>
          	<td>[70-180]</td>
          	<td>(180-400]</td>
        </tr>
        <tr>
          <td rowspan=3><b>Rate of change of the<br>previous 3 BG values <br>(mg/dL/min)</b></td>
          	<td>< -1</td>
          	<td>[40-70) <br>&<br> < -1 </td>
          	<td>[70-180] <br>&<br> < -1 </td>
            <td>(180-400] <br>&<br> < -1 </td>
        </tr>
        <tr>
            <td>[-1 to 1]</td>
          	<td>[40-70) <br>&<br> [-1 to 1]</td>
          	<td>[70-180] <br>&<br> [-1 to 1]</td>
            <td>(180-400] <br>&<br> [-1 to 1]</td>
        </tr>
        <tr>
            <td>> 1</td>
          	<td>[40-70) <br>&<br> > 1</td>
          	<td>[70-180] <br>&<br> > 1</td>
            <td>(180-400] <br>&<br> > 1</td>
        </tr>
    </tbody>
</table>



## Finding Snapshots Algorithm

The algorithm for finding a snapshot is as follows

- Fit the CGM trace to a 5-minute time series to uncover gaps
- Calculate the median mg/dL value with a 30-minute (6 cgm points) rolling window 
- Calculate the slope in mg/dL/min with a 15-minute (3 cgm points) rolling window
- Apply one of the 9 conditions labels to each CGM point
- Calculate the max gap size of the cgm trace in a 48 hour *centered* rolling window (where the evaluation point is in the center)
- Randomly select one evaluation point for each condition that does not overlap with any other 48-hour snapshot and has a max gap <= 15 minutes