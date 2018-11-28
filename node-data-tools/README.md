# @tidepool/data-tools

Node streams to work with [Tidepool](https://tidepool.org) API data

## Installation

``` bash
$ npm install @tidepool/data-tools
```

## Example

``` js
import TidepoolDataTools from '@tidepool/data-tools';

// Set up the processing stream
const processingStream = readStream
      .pipe(TidepoolDataTools.jsonParser())
      .pipe(TidepoolDataTools.tidepoolProcessor());

// Now attach multiple parallel output streams
processingStream
        .pipe(TidepoolDataTools.xlsxStreamWriter(xlsxStream));

processingStream
        .pipe(someOtherOutputStream);
```

## Methods

### TidepoolDataTools.jsonParser()

Convenience function to return a `JSONStream.parse('*')`.  
See also the [JSONStream NPM Module](https://www.npmjs.com/package/JSONStream).

### TidepoolDataTools.tidepoolProcessor()

Returns a `through` stream that processes the JSON Object data according the the config.

### TidepoolDataTools.xlsxStreamWriter(outputStream)

Writes an xlsx Workbook to `outputStream` with different Worksheets according to the config.

## Command Line Usage

`@tidepool/data-tools` includes a command-line tool
<!--
[`npx`](https://ghub.io/npx):

```sh
npx flat foo.json
```

Or install globally:
-->

Install globally:
 
```sh
$ npm i -g @tidepool/data-tools && tidepool-data-tools --help
Usage: tidepool-data-tools [options] [command]

Options:
  -V, --version      output the version number
  -h, --help         output usage information

Commands:
  convert [options]  Convert data between different formats

$ tidepool-data-tools convert --help
Usage: tidepool-data-tools [options]

Options:
  -V, --version                            output the version number
  -i, --input-tidepool-data <file>         csv, xlsx, or json file that contains Tidepool data
  -c, --config <file>                      a JSON file that contains the field export configuration
  --salt <salt>                            salt used in the hashing algorithm (default: "no salt specified")
  -o, --output-data-path <path>            the path where the data is exported (default: "./example-data/export")
  -f, --output-format <format>             the path where the data is exported (default: ["all"])
  --start-date [date]                      filter data by startDate
  --end-date [date]                        filter data by endDate
  --merge-wizard-data                      option to merge wizard data with bolus data. Default is true
  --filterByDatesExceptUploadsAndSettings  upload and settings data can occur before and after start and end dates, so include ALL upload and settings data in export
  -h, --help                               output usage information
```

## License
Licensed under the BSD-2-Clause License
