import _ from 'lodash';
import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import mkdirp from 'mkdirp';
import moment from 'moment';
import events from 'events';
import program from 'commander';
import JSONStream from 'JSONStream';
import es from 'event-stream';
import flatten from 'flat';
import Excel from 'exceljs';
import * as CSV from 'csv-string';
import config from './config.json';
/* eslint no-console: ["error", { allow: ["warn", "error", "info"] }] */

const MMOL_TO_MGDL = 18.01559;

// TODO: Having this as a class seems to slow down performance
export default class TidepoolDataTools {
  static fieldsToStringify(type) {
    return Object.keys(_.pickBy(config[type], n => n.stringify));
  }

  static get allFields() {
    return _.chain(config)
      .flatMap(field => Object.keys(field))
      .uniq()
      .sort()
      .value();
  }

  static stringifyFields(data) {
    _.each(
      _.chain(data)
        .pick(this.fieldsToStringify(data.type))
        .keys()
        .value(),
      item => _.set(data, item, JSON.stringify(data[item])),
    );
  }

  static normalizeBgData(data, units) {
    let conversion = 1;
    let precision = 1;
    if (units === 'mg/dL') {
      conversion = MMOL_TO_MGDL;
      precision = 0;
    }
    if (data.units) {
      if (typeof data.units === 'string' && data.units !== units) {
        _.assign(data, {
          units,
        });
      }
      if (typeof data.units === 'object' && data.units.bg && data.units.bg === units) {
        _.assign(data.units.bg, units);
      }
    }
    switch (data.type) {
      case 'cbg':
      case 'smbg':
      case 'deviceEvent':
        if (data.value) {
          _.assign(data, {
            value: _.round(data.value * conversion, precision),
          });
        }
        break;
      case 'wizard':
        if (data.bgInput) {
          _.assign(data, {
            bgInput: _.round(data.bgInput * conversion, precision),
          });
        }
        if (data.insulinSensitivity) {
          _.assign(data, {
            insulinSensitivity: _.round(data.insulinSensitivity * conversion, precision),
          });
        }
        if (data.bgTarget) {
          const bgTarget = _.cloneDeep(typeof data.bgTarget === 'string' ? JSON.parse(data.bgTarget) : data.bgTarget);
          _.assign(bgTarget, {
            high: _.round(bgTarget.high * conversion, precision),
            low: _.round(bgTarget.low * conversion, precision),
          });
          _.assign(data, {
            bgTarget: typeof data.bgTarget === 'string' ? JSON.stringify(bgTarget) : bgTarget,
          });
        }
        break;
      case 'pumpSettings':
        if (data.bgTarget) {
          const bgTargets = _.cloneDeep(typeof data.bgTarget === 'string' ? JSON.parse(data.bgTarget) : data.bgTarget);
          for (let idx = 0; idx < bgTargets.length; idx++) {
            _.assign(bgTargets[idx], {
              high: _.round(bgTargets[idx].high * conversion, precision),
              low: _.round(bgTargets[idx].low * conversion, precision),
            });
          }
          _.assign(data, {
            bgTarget: typeof data.bgTarget === 'string' ? JSON.stringify(bgTargets) : bgTargets,
          });
        }
        if (data.insulinSensitivity) {
          const isfs = _.cloneDeep(typeof data.insulinSensitivity === 'string' ? JSON.parse(data.insulinSensitivity) : data.insulinSensitivity);
          for (let idx = 0; idx < isfs.length; idx++) {
            _.assign(isfs[idx], {
              amount: _.round(isfs[idx].amount * conversion, precision),
            });
          }
          _.assign(data, {
            insulinSensitivity: typeof data.insulinSensitivity === 'string' ? JSON.stringify(isfs) : isfs,
          });
        }
        break;
      default:
        break;
    }
  }

  static flatMap(data, toFields) {
    return _.pick(flatten(data, {
      maxDepth: 2,
    }), toFields);
  }

  static jsonParser() {
    return JSONStream.parse('*');
  }

  static tidepoolProcessor(processorConfig = {}) {
    return es.mapSync((data) => {
      // Stringify objects configured with { "stringify": true }
      this.stringifyFields(data);
      // Convert BGL data to mg/dL if configured to do so
      if (processorConfig.bgUnits) {
        this.normalizeBgData(data, processorConfig.bgUnits);
      }
      // Return flattened layout mapped to all fields in the config
      return this.flatMap(data, this.allFields);
    });
  }

  static xlsxStreamWriter(outStream) {
    const options = {
      stream: outStream,
      useStyles: true,
      useSharedStrings: true,
    };
    const wb = new Excel.stream.xlsx.WorkbookWriter(options);

    return es.through(
      (data) => {
        if (data.type) {
          let sheet = wb.getWorksheet(data.type);
          if (_.isUndefined(sheet)) {
            sheet = wb.addWorksheet(data.type, {
              views: [{
                state: 'frozen',
                xSplit: 0,
                ySplit: 1,
                topLeftCell: 'A2',
                activeCell: 'A2',
              }],
            });
            try {
              sheet.columns = Object.keys(config[data.type]).map(field => ({
                header: field,
                key: field,
                width: 22,
              }));
              sheet.getRow(1).font = {
                bold: true,
              };
              // FIXME: use the right columns
              sheet.getColumn(1).numFmt = 'yyyy-mm-ddThh:mm:ss';
              sheet.getColumn(2).numFmt = 'yyyy-mm-ddThh:mm:ss';
            } catch (e) {
              if (e instanceof TypeError) {
                console.warn(`Warning: configuration ignores data type: '${data.type}'`);
              } else {
                throw e;
              }
            }
          }
          // Convert timestamps to Excel Dates
          if (data.time) {
            _.assign(data, {
              time: moment(data.time).toDate(),
            });
          }
          if (data.deviceTime) {
            _.assign(data, {
              deviceTime: moment.utc(data.deviceTime).toDate(),
            });
          }
          if (data.computerTime) {
            _.assign(data, {
              computerTime: moment.utc(data.computerTime).toDate(),
            });
          }
          sheet.addRow(data).commit();
        } else {
          console.warn(`Invalid data type specified: '${JSON.stringify(data)}'`);
        }
      },
      async function end() {
        await wb.commit();
        this.emit('end');
      },
    );
  }
}

function convert(command) {
  if (!command.inputTidepoolData) command.help();

  const inFilename = path.basename(command.inputTidepoolData, '.json');
  const outFilename = path.join(command.outputDataPath,
    crypto
      .createHash('sha256')
      .update(`${inFilename}${command.salt}`)
      .digest('hex'));

  const readStream = fs.createReadStream(command.inputTidepoolData);

  readStream.on('error', () => {
    console.error(`Could not read input file '${command.inputTidepoolData}'`);
    process.exit(1);
  });

  readStream.on('open', () => {
    if (!fs.existsSync(command.outputDataPath)) {
      mkdirp.sync(command.outputDataPath, (err) => {
        if (err) {
          console.error(`Could not create export output path '${command.outputDataPath}'`);
          process.exit(1);
        }
      });
    }

    let counter = 0;

    // Data processing
    events.EventEmitter.defaultMaxListeners = 3;
    const processingStream = readStream
      .pipe(TidepoolDataTools.jsonParser())
      .pipe(TidepoolDataTools.tidepoolProcessor({ bgUnits: 'mmol/L' }));
      // .pipe(TidepoolDataTools.tidepoolProcessor({ bgUnits: 'mg/dL' }));

    events.EventEmitter.defaultMaxListeners += 1;
    processingStream
      .pipe(es.mapSync(() => {
        counter += 1;
      }));

    // Single CSV
    if (_.includes(command.outputFormat, 'csv') || _.includes(command.outputFormat, 'all')) {
      events.EventEmitter.defaultMaxListeners += 2;
      const csvStream = fs.createWriteStream(`${outFilename}.csv`);
      csvStream.write(CSV.stringify(TidepoolDataTools.allFields));
      processingStream
        .pipe(es.mapSync(
          data => CSV.stringify(TidepoolDataTools.allFields.map(field => data[field] || '')),
        ))
        .pipe(csvStream);
    }

    // Multiple CSVs
    if (_.includes(command.outputFormat, 'csvs') || _.includes(command.outputFormat, 'all')) {
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
    if (_.includes(command.outputFormat, 'xlsx') || _.includes(command.outputFormat, 'all')) {
      const xlsxStream = fs.createWriteStream(`${outFilename}.xlsx`);

      events.EventEmitter.defaultMaxListeners += 1;
      processingStream
        .pipe(TidepoolDataTools.xlsxStreamWriter(xlsxStream));
    }

    readStream.on('end', () => {
      console.info(`Exported ${counter} records.`);
    });
  });
}

/*
function getData() {
  // Implement this command
}
*/

if (require.main === module) {
  program
    .name('tidepool-data-tools')
    .version('0.1.0');

  let commandInvoked = false;

  program
    .command('convert')
    .description('Convert data between different formats')
    .option('-i, --input-tidepool-data <file>', 'csv, xlsx, or json file that contains Tidepool data')
    .option('-c, --config <file>', 'a JSON file that contains the field export configuration')
    .option('--salt <salt>', 'salt used in the hashing algorithm', 'no salt specified')
    .option('-o, --output-data-path <path>', 'the path where the data is exported',
      path.join(__dirname, 'example-data', 'export'))
    .option('-f, --output-format <format>', 'the format of file to export to. Can be xlsx, csv, csvs or all. Can be specified multiple times', (val, list) => {
      if (list[0] === 'all' && list.length === 1) {
        list.splice(0);
      }
      list.push(val);
      return list;
    }, ['all'])
    // TODO: Implement options below this TODO
    .option('--start-date [date]', 'filter data by startDate')
    .option('--end-date [date]', 'filter data by endDate')
    .option('--merge-wizard-data', 'option to merge wizard data with bolus data. Default is true')
    .option(
      '--filterByDatesExceptUploadsAndSettings',
      'upload and settings data can occur before and after start and end dates, so include ALL upload and settings data in export',
    )
    .action((command, options) => {
      convert(command, options);
      commandInvoked = true;
    });

  /*
  program
    .command('getdata')
    .description('Get data from the Tidepool API')
    .option('-e, --env <envirnoment>',
      'Environment to pull the Tidepool data from. dev, stg, int or prd')
    .action((command, options) => {
      getData(command, options);
      commandInvoked = true;
    });
  */

  program
    .parse(process.argv);

  if (!commandInvoked) {
    program.outputHelp();
  }
}
