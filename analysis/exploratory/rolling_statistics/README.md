# Rolling Statistics
A set of tools to calculate and visualize rolling statistics of cgm and pump data from Tidepool.

## Usage
**rolling_statistics.py** arguments:  
`-d`: Path location containing data to be analyzed  
`-i`:  Input filename of .csv to analyze  
`-o`: Output location where the results will be stored  
`-om`: Output mode - Three output files available: ( R )olling, ( D )aily, ( S )ummary  
`-s`: Output summary .csv filename to append summary statistics  
`-ds`: The start of the 24-hour day period (24 hour format)  
`-rw`: An array of rolling window strings  

Example:
`python rolling_statistics.py -d tidepool-data -i file1.csv -o ./output_results/ -om DS -s summaryOutput -ds 5:55 -rw 24hr 7day 30day 90day`

## dependencies:
* set up tidepool-analytics virtual environment (see /data-analytics/readme.md)
* Tidepool .csv format with est.localTime
