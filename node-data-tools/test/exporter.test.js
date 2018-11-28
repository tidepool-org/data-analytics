import _ from 'lodash';
import program from 'commander';
import fs from 'fs';
import Excel from 'exceljs';
import { unflatten } from 'flat';
import { diffString } from 'json-diff';

program
  .version('0.1.0')
  .option('-i, --input-data <file>', 'csv, xlsx, or json file that contains Tidepool data')
  .option('-o, --output-data <file>', 'the file that was exported by the exporter')
  .option('-v, --verbose', 'show differences between files')
  .parse(process.argv);

const sortedInputData = _.sortBy(
  JSON.parse(fs.readFileSync(program.inputData, 'utf8')),
  obj => obj.time + obj.type,
);

const outputData = [];
let sortedOutputData = [];
let diffCount = 0;
const excludedFields = [
  '_deduplicator',
  '_dataState',
  'createdUserId',
  'deletedTime',
  'deletedUserId',
  'modifiedUserId',
  '_state',
  'state',
  'client',
  'dataSetType',
  'guid',
  'clockDriftOffset',
  'conversionOffset',
];

const wb = new Excel.Workbook();

(async () => {
  await wb.xlsx.readFile(program.outputData);
  wb.eachSheet((worksheet) => {
    const headings = _.drop(worksheet.getRow(1).values);
    worksheet.eachRow((row, rowNumber) => {
      // Skip the header
      if (rowNumber > 1) {
        let valueIdx = 1;
        const data = unflatten(_.omitBy(_.reduce(headings, (object, key) => {
          let cellValue = row.values[valueIdx];
          try {
            cellValue = JSON.parse(cellValue);
            if (typeof cellValue !== 'object') {
              cellValue = row.values[valueIdx];
            }
          } catch (e) {
            // Don't care.
          }
          // eslint-disable-next-line no-param-reassign
          object[key] = cellValue;
          valueIdx += 1;
          return object;
        }, {}), _.isUndefined));
        outputData.push(data);
      }
    });

    sortedOutputData = _.sortBy(outputData, obj => obj.time + obj.type);
  });

  if (sortedInputData.length !== sortedOutputData.length) {
    console.log('Number of input and output records don\'t match!');
    process.exit(1);
  }

  for (let i = 0; i < sortedInputData.length; i++) {
    const diff = diffString(_.omit(sortedInputData[i], excludedFields), sortedOutputData[i]);
    if (diff) {
      diffCount += 1;
      console.log(`'${sortedInputData[i].type}' record at ${sortedInputData[i].time} differs`);
      if (program.verbose) {
        console.log(diff);
      }
    }
  }

  console.log(`There were ${diffCount} differences between ${sortedInputData.length} records.`);
  if (diffCount === 0) {
    process.exit(0);
  } else {
    process.exit(1);
  }
})();
