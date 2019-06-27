import _ from 'lodash';
import moment from 'moment';
import program from 'commander';
import { promisify } from 'util';
import fs from 'fs';
import Excel from 'exceljs';
import { unflatten } from 'flat';
import { diffString } from 'json-diff';
import TidepoolDataTools from '../index';

program
  .version('0.1.0')
  .option('-i, --input-data <file>', 'json file that contains Tidepool data')
  .option('-o, --output-data <file>', 'the file that was exported by the exporter')
  .option('-u, --units <units>', 'BG Units (mg/dL|mmol/L)', (value) => {
    if (_.indexOf(['mmol/L', 'mg/dL'], value) < 0) {
      console.error('Units must be "mg/dL" or "mmol/L"');
      process.exit(1);
    }
    return value;
  }, 'mmol/L')
  .option('-v, --verbose', 'show differences between files')
  .parse(process.argv);

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
];

const wb = new Excel.Workbook();

(async () => {
  const readFile = promisify(fs.readFile);
  const inputFile = await readFile(program.inputData, 'utf8');
  const headingsToFields = _.mapValues(TidepoolDataTools.cache.fieldHeader, item => _.invert(item));
  const sheetNameToType = _.invert(TidepoolDataTools.cache.typeDisplayName);
  const sortedInputData = _.sortBy(
    JSON.parse(inputFile),
    obj => obj.id + obj.type,
  );
  // eslint-disable-next-line no-restricted-syntax
  for (const data of sortedInputData) {
    TidepoolDataTools.normalizeBgData(data, program.units);
    // Normalize `time` field (turn it into UTC)
    data.time = moment(data.time).utc().toISOString();
  }

  await wb.xlsx.readFile(program.outputData);
  wb.eachSheet((worksheet) => {
    // Ignore the "EXPORT ERROR" sheet
    if (worksheet.name === 'EXPORT ERROR') {
      return;
    }
    const headings = _.drop(worksheet.getRow(1).values);
    const type = sheetNameToType[worksheet.name] || worksheet.name;
    const fields = _.map(headings, value => headingsToFields[type][value] || value);
    worksheet.eachRow((row, rowNumber) => {
      // Skip the header
      if (rowNumber > 1) {
        let valueIdx = 1;
        const data = unflatten(_.omitBy(_.reduce(fields, (object, key) => {
          let cellValue = row.values[valueIdx];
          if (_.indexOf(['deviceTime', 'computerTime'], fields[valueIdx - 1]) >= 0) {
            cellValue = moment.utc(cellValue).format('YYYY-MM-DDTHH:mm:ss');
          } else if (fields[valueIdx - 1] === 'time') {
            // Normalize `time` field (turn it into UTC)
            cellValue = moment(cellValue).utc().toISOString();
          } else {
            try {
              cellValue = JSON.parse(cellValue);
              if (typeof cellValue !== 'object') {
                cellValue = row.values[valueIdx];
              }
            } catch (e) {
              // Don't care.
            }
          }
          // eslint-disable-next-line no-param-reassign
          object[key] = cellValue;
          valueIdx += 1;
          return object;
        }, {}), _.isUndefined));
        outputData.push(data);
      }
    });

    sortedOutputData = _.sortBy(outputData, obj => obj.id + obj.type);
  });

  if (sortedInputData.length !== sortedOutputData.length) {
    console.log('Number of input and output records don\'t match!');
  }

  for (let i = 0; i < sortedInputData.length; i++) {
    const diff = diffString(_.omit(sortedInputData[i], excludedFields), sortedOutputData[i]);
    if (diff) {
      diffCount += 1;
      console.log(`'${sortedInputData[i].type}' record (ID: ${sortedInputData[i].id}) at ${sortedInputData[i].time} differs`);
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
