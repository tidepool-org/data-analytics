import _ from 'lodash';
import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import mkdirp from 'mkdirp';
import events from 'events';
import program from 'commander';
import JSONStream from 'JSONStream';
import es from 'event-stream';
import flatten from 'flat';
import Excel from 'exceljs';
import * as CSV from 'csv-string';
import config from './config.json';
/* eslint no-console: ["error", { allow: ["warn", "error", "info"] }] */

function stringifyFields(data, fieldsToStringify) {
  _.each(
    _.chain(data)
      .pick(fieldsToStringify)
      .keys()
      .value(),
    item => _.set(data, item, JSON.stringify(data[item])),
  );
}

function flatMap(data, toFields) {
  return _.pick(flatten(data, {
    maxDepth: 2,
  }), toFields);
}

const allFields = _.chain(config)
  .flatMap(field => Object.keys(field))
  .uniq()
  .sort()
  .value();

if (require.main === module) {
  program
    .version('0.1.0')
    .option('-i, --input-tidepool-data <file>', 'csv, xlsx, or json file that contains Tidepool data')
    .option('-c', '--config <file>', 'a JSON file that contains the field export configuration')
    .option('--salt <salt>', 'salt used in the hashing algorithm', 'no salt specified')
    .option('-o, --output-data-path <path>', 'the path where the data is exported',
      path.join(__dirname, 'example-data', 'export'))
    .option('-f, --output-format <format>', 'the path where the data is exported', (val, list) => {
      list.push(val);
      return list;
    }, [])
    /*
    .option('--start-date [date]', 'filter data by startDate and EndDate')
    .option('--end-date [date]', 'filter data by startDate and EndDate')
    .option('--merge-wizard-data', 'option to merge wizard data with bolus data. Default is true')
    .option(
      '--filterByDatesExceptUploadsAndSettings',
      'upload and settings data can occur before and after start and end dates, so include ALL upload and settings data in export',
    )
    */
    .parse(process.argv);

  if (!program.inputTidepoolData) program.help();
  if (!program.outputFormat.length) {
    program.outputFormat.push('all');
  }

  const inFilename = path.basename(program.inputTidepoolData, '.json');
  const outFilename = path.join(program.outputDataPath,
    crypto
      .createHash('sha256')
      .update(`${inFilename}${program.salt}`)
      .digest('hex'));

  const readStream = fs.createReadStream(program.inputTidepoolData);

  readStream.on('error', () => {
    console.error(`Could not read input file '${program.inputTidepoolData}'`);
    process.exit(1);
  });

  readStream.on('open', () => {
    if (!fs.existsSync(program.outputDataPath)) {
      mkdirp.sync(program.outputDataPath, (err) => {
        if (err) {
          console.error(`Could not create export output path '${program.outputDataPath}'`);
          process.exit(1);
        }
      });
    }

    let counter = 0;

    // Data processing
    const parser = JSONStream.parse('*');
    const fieldsToStringify = _.flatMap(
      config,
      field => Object.keys(
        _.pickBy(field, n => n.stringify),
      ),
    );

    events.EventEmitter.defaultMaxListeners = 3;
    const processingStream = readStream
      .pipe(parser)
      .pipe(es.mapSync((data) => {
        // Stringify objects configured with { "stringify": true }
        stringifyFields(data, fieldsToStringify);
        // Return flattened layout mapped to all fields in the config
        return flatMap(data, allFields);
      }));

    // Single CSV
    if (_.includes(program.outputFormat, 'csv') || _.includes(program.outputFormat, 'all')) {
      events.EventEmitter.defaultMaxListeners += 2;
      const csvStream = fs.createWriteStream(`${outFilename}.csv`);
      csvStream.write(CSV.stringify(allFields));
      processingStream
        .pipe(es.mapSync((data) => {
          counter += 1;
          return CSV.stringify(allFields.map(field => data[field] || ''));
        }))
        .pipe(csvStream);
    }

    // Multiple CSVs
    if (_.includes(program.outputFormat, 'csvs') || _.includes(program.outputFormat, 'all')) {
      if (!fs.existsSync(outFilename)) {
        fs.mkdirSync(outFilename);
      }
      Object.keys(config).forEach((key) => {
        const csvStream2 = fs.createWriteStream(`${outFilename}/${key}.csv`);
        csvStream2.write(CSV.stringify(Object.keys(config[key])));
        events.EventEmitter.defaultMaxListeners += 2;
        processingStream
          // eslint-disable-next-line consistent-return
          .pipe(es.mapSync((data) => {
            if (data.type === key) {
              return CSV.stringify(Object.keys(config[key]).map(field => data[field] || ''));
            }
          }))
          .pipe(csvStream2);
      });
    }

    // XLSX
    if (_.includes(program.outputFormat, 'xlsx') || _.includes(program.outputFormat, 'all')) {
      const xlsxStream = fs.createWriteStream(`${outFilename}.xlsx`);
      const options = {
        stream: xlsxStream,
        useStyles: true,
        useSharedStrings: true,
      };
      const wb = new Excel.stream.xlsx.WorkbookWriter(options);

      events.EventEmitter.defaultMaxListeners += 1;
      processingStream
        .pipe(es.mapSync((data) => {
          if (data.type) {
            let sheet = wb.getWorksheet(data.type);
            if (_.isUndefined(sheet)) {
              sheet = wb.addWorksheet(data.type);
              try {
                sheet.columns = Object.keys(config[data.type]).map(field => ({
                  header: field,
                  key: field,
                }));
              } catch (e) {
                console.warn(`Warning: configuration ignores data type: '${data.type}'`);
              }
            }
            sheet.addRow(data).commit();
          } else {
            console.warn(`Invalid data type specified: '${JSON.stringify(data)}'`);
          }
        }));

      processingStream.on('end', async () => {
        await wb.commit();
      });
    }

    readStream.on('end', () => {
      console.info(`Exported ${counter} records.`);
    });
  });
}
