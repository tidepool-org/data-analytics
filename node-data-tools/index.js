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

export default class TidepoolDataTools {
  static typeDisplayName(type) {
    return this.cache.typeDisplayName[type];
  }

  static fieldHeader(type, field) {
    return this.cache.fieldHeader[type][field];
  }

  static fieldWidth(type, field) {
    return this.cache.fieldWidth[type][field];
  }

  static cellFormat(type, field, data = {}) {
    try {
      return _.template(this.cache.cellFormat[type][field])(data);
    } catch (err) {
      console.error(`Error in cellFormat with data: ${JSON.stringify(data)}`);
      console.error(`Template processing error: ${err}`);
      return '';
    }
  }

  static fieldsToStringify(type) {
    return this.cache.fieldsToStringify[type];
  }

  static get allFields() {
    return this.cache.allFields;
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

  static addLocalTime(data) {
    const localTime = new Date(data.time);
    localTime.setUTCMinutes(localTime.getUTCMinutes() + data.timezoneOffset);
    _.assign(data, {
      localTime,
    });
  }

  static transformData(data, options = {}) {
    const transformFunction = this.cache.transformData[data.type];
    if (transformFunction) {
      try {
        _.assign(data, transformFunction({ data, options }));
      } catch (err) {
        console.error(`Error in transformData with data: ${JSON.stringify(data)}`);
        console.error(`Template processing error: ${err}`);
      }
    }
  }

  static normalizeBgData(data, units) {
    // TODO: conversion should be done with config and a mapping function
    let conversion = 1;
    if (units === 'mg/dL') {
      conversion = MMOL_TO_MGDL;
    }
    if (data.units && data.type !== 'bloodKetone') {
      if (typeof data.units === 'string' && data.units !== units) {
        _.set(data, 'units', units);
      }
      if (typeof data.units === 'object' && data.units.bg && data.units.bg !== units) {
        _.set(data, 'units.bg', units);
      }
    }
    switch (data.type) {
      case 'cbg':
      case 'smbg':
      case 'deviceEvent':
        if (data.value) {
          _.assign(data, {
            value: data.value * conversion || '',
          });
        }
        break;
      case 'wizard':
        if (data.bgInput) {
          _.assign(data, {
            bgInput: data.bgInput * conversion || '',
          });
        }
        if (data.insulinSensitivity) {
          _.assign(data, {
            insulinSensitivity: data.insulinSensitivity * conversion || '',
          });
        }
        if (data.bgTarget) {
          const bgTarget = _.cloneDeep(typeof data.bgTarget === 'string' ? JSON.parse(data.bgTarget) : data.bgTarget);
          _.assign(bgTarget, {
            high: bgTarget.high * conversion || '',
            low: bgTarget.low * conversion || '',
          });
          _.assign(data, {
            bgTarget: typeof data.bgTarget === 'string' ? JSON.stringify(bgTarget) : bgTarget,
          });
        }
        break;
      case 'pumpSettings.bgTarget':
        if (data.bgTarget) {
          const bgTarget = _.cloneDeep(typeof data.bgTarget === 'string' ? JSON.parse(data.bgTarget) : data.bgTarget);
          _.assign(bgTarget, {
            high: bgTarget.high * conversion || '',
            low: bgTarget.low * conversion || '',
            target: bgTarget.target * conversion || '',
            range: bgTarget.range * conversion || '',
          });
          _.assign(data, {
            bgTarget: typeof data.bgTarget === 'string' ? JSON.stringify(bgTarget) : bgTarget,
          });
        }
        break;
      case 'pumpSettings.insulinSensitivity':
        if (data.insulinSensitivity) {
          const isf = _.cloneDeep(typeof data.insulinSensitivity === 'string' ? JSON.parse(data.insulinSensitivity) : data.insulinSensitivity);
          _.assign(isf, {
            amount: isf.amount * conversion || '',
          });
          _.assign(data, {
            insulinSensitivity: typeof data.insulinSensitivity === 'string' ? JSON.stringify(isf) : isf,
          });
        }
        break;
      default:
        break;
    }
  }

  static splitPumpSettingsData() {
    return es.through(
      function write(data) {
        if (data.type === 'pumpSettings') {
          this.pause();
          const commonFields = _.omit(data, ['basalSchedules', 'bgTarget', 'carbRatio', 'insulinSensitivity', 'units']);
          /* eslint-disable no-restricted-syntax */
          for (const scheduleName of _.keys(data.basalSchedules)) {
            for (const basalSchedule of data.basalSchedules[scheduleName]) {
              const emitData = _.assign({ scheduleName, basalSchedule }, commonFields);
              emitData.type = 'pumpSettings.basalSchedules';
              this.emit('data', emitData);
            }
          }
          for (const bgTarget of data.bgTarget) {
            const emitData = _.assign({ bgTarget, units: data.units }, commonFields);
            emitData.type = 'pumpSettings.bgTarget';
            this.emit('data', emitData);
          }
          for (const carbRatio of data.carbRatio) {
            const emitData = _.assign({ carbRatio, units: data.units }, commonFields);
            emitData.type = 'pumpSettings.carbRatio';
            this.emit('data', emitData);
          }
          for (const insulinSensitivity of data.insulinSensitivity) {
            const emitData = _.assign({ insulinSensitivity, units: data.units }, commonFields);
            emitData.type = 'pumpSettings.insulinSensitivity';
            this.emit('data', emitData);
          }
          /* eslint-enable no-restricted-syntax */
          this.resume();
        } else {
          this.emit('data', data);
        }
      },
      function end() {
        this.emit('end');
      },
    );
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
      // Synthesize the 'localTime' field
      this.addLocalTime(data);
      // Stringify objects configured with { "stringify": true }
      this.stringifyFields(data);
      // Convert BGL data to mg/dL if configured to do so
      if (processorConfig.bgUnits) {
        this.normalizeBgData(data, processorConfig.bgUnits);
      }
      this.transformData(data, processorConfig);
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

    // Create the error sheet first, and hide it.
    // We create this up front, so that if the user experiences an error, this is the
    // first sheet they see when they open the XLSX.
    const errorSheet = wb.addWorksheet('EXPORT ERROR');
    (async () => {
      await errorSheet.addRow(['The Export tool took too long to complete. Please send an email to support@tidepool.org and we\'ll help you out.']).commit();
      errorSheet.state = 'veryHidden';
    })();

    outStream.on('timeout', () => {
      // Unhide the error sheet
      errorSheet.state = 'visible';
    });

    return es.through(
      (data) => {
        if (data.type) {
          const sheetName = this.typeDisplayName(data.type);
          if (_.isUndefined(sheetName)) {
            console.warn(`Warning: configuration ignores data type: '${data.type}'`);
            return;
          }
          let sheet = wb.getWorksheet(sheetName);
          if (_.isUndefined(sheet)) {
            sheet = wb.addWorksheet(sheetName, {
              views: [{
                state: 'frozen',
                xSplit: 0,
                ySplit: 1,
                topLeftCell: 'A2',
                activeCell: 'A2',
              }],
            });
            sheet.columns = Object.keys(config[data.type].fields).map(field => ({
              header: this.fieldHeader(data.type, field),
              key: field,
              width: this.fieldWidth(data.type, field),
              style: { numFmt: this.cellFormat(data.type, field, data) },
            }));
            sheet.getRow(1).font = {
              bold: true,
            };
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
          console.warn(`No data type specified: '${JSON.stringify(data)}Invalid'`);
        }
      },
      async function end() {
        await wb.commit();
        this.emit('end');
      },
    );
  }
}

TidepoolDataTools.cache = {
  allFields: _.chain(config)
    .flatMap(field => Object.keys(field.fields))
    .uniq()
    .sort()
    .value(),
  fieldsToStringify: _.mapValues(
    config, item => Object.keys(_.pickBy(item.fields, n => n.stringify)),
  ),
  typeDisplayName: _.mapValues(config, (item, key) => item.displayName || _.chain(key).replace(/([A-Z])/g, ' $1').startCase().value()),
  fieldHeader: _.mapValues(
    config, type => _.mapValues(type.fields,
      (item, key) => item.header || _.chain(key).replace(/([A-Z])/g, ' $1').replace('.', ' ').startCase()
        .value()),
  ),
  fieldWidth: _.mapValues(
    config, type => _.mapValues(type.fields, item => item.width || 22),
  ),
  cellFormat: _.mapValues(
    config, type => _.mapValues(type.fields, item => item.cellFormat || undefined),
  ),
  transformData:
    _.mapValues(config, item => (item.transform ? _.template(item.transform) : undefined)),
};

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
      .pipe(TidepoolDataTools.splitPumpSettingsData())
      .pipe(TidepoolDataTools.tidepoolProcessor({ bgUnits: command.units }));

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
        const csvStream2 = fs.createWriteStream(`${outFilename}/${TidepoolDataTools.typeDisplayName(key)}.csv`);
        csvStream2.write(CSV.stringify(Object.keys(config[key].fields)));
        events.EventEmitter.defaultMaxListeners += 2;
        processingStream
          // eslint-disable-next-line consistent-return
          .pipe(es.mapSync((data) => {
            if (data.type === key) {
              return CSV.stringify(Object.keys(config[key].fields).map(field => data[field] || ''));
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
    .option('-u, --units <units>', 'BG Units (mg/dL|mmol/L)', (value) => {
      if (_.indexOf(['mmol/L', 'mg/dL'], value) < 0) {
        console.error('Units must be "mg/dL" or "mmol/L"');
        process.exit(1);
      }
      return value;
    }, 'mmol/L')
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
