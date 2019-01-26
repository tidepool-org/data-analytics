from .loop_report_parser import parse_loop_report, Sections
import os
import re
import json

class LoopReport:

    def __init__(self, path_and_file_name: str):

        self.__path_and_file_name = path_and_file_name
        self.__loop_report_dict: dict = {}
        self.__carb_ratio_schedule: dict = {}
        self.__insuline_sensitivity_schedule: dict = {}
        try:
            self.__parse()
        except IsADirectoryError:
            raise RuntimeError('The file path and name passed in is invalid.')
        except:
            raise


    @property
    def carb_ratio_schedule(self) -> dict:
        return self.__carb_ratio_schedule

    @property
    def insuline_sensitivity_schedule(self) -> dict:
        return self.__insuline_sensitivity_schedule
               
    @property
    def loop_report_dict(self) -> dict:
        return self.__loop_report_dict

    def __parse(self):
        dict = parse_loop_report(os.path.realpath(self.__path_and_file_name))
        if Sections.LOOP_VERSION in dict:
            try:
                self.__loop_report_dict["loop_version"] = dict[Sections.LOOP_VERSION][Sections.LOOP_VERSION]
            except:
                print("handled error loop_version")

        if Sections.DEVICE_DATA_MANAGER in dict:
            try:
                self.__device_data_manager = dict[Sections.DEVICE_DATA_MANAGER]
            except:
                print("handled error device data manager")

        if Sections.RILEY_LINK_DEVICE in dict:
            try:
                riley_link_device = dict[Sections.RILEY_LINK_DEVICE]
                self.__loop_report_dict["radio_firmware"] = riley_link_device["radioFirmware"].strip()
                self.__loop_report_dict["ble_firmware"] = riley_link_device["bleFirmware"].strip()
            except:
                print("handled error riley link device")

        if Sections.CARB_STORE in dict:
            try:
                carb_store = dict[Sections.CARB_STORE]
                self.__carb_ratio_schedule = json.loads(carb_store["carbRatioSchedule"].replace("[", "{").
                                                         replace("]", "}").replace("{{", "{").replace("}}", "}"))

                default_absorption_times = json.loads(carb_store["defaultAbsorptionTimes"].replace("(", "{")
                                                      .replace(")", "}").replace("fast", '"fast"').
                                                      replace("medium", '"medium"').replace("slow", '"slow"'))
                self.__loop_report_dict["default_absorption_times_fast"] = default_absorption_times["fast"]
                self.__loop_report_dict["default_absorption_times_medium"] = default_absorption_times["medium"]
                self.__loop_report_dict["default_absorption_times_slow"] = default_absorption_times["slow"]

                temp = carb_store["insulinSensitivitySchedule"].replace("[", "{").replace("]", "}").replace("{{", "{").\
                    replace("}}", "}").replace('"items": {{', '"items": [{').replace('"items": {', '"items": [{').\
                    replace("}}", "}]")\
                    .replace('}, "unit"', '}], "unit"').replace('}, "timeZone"', '}], "timeZone"')


                if temp[-1:] != '}':
                    temp = temp + '}'
                self.__insuline_sensitivity_schedule = json.loads(temp)

            except:
                print("handled error carb store")

        if Sections.DOSE_STORE in dict:
            try:
                dose_store = dict[Sections.DOSE_STORE]
                self.__basal_profile = json.loads(dose_store["basalProfile"].replace("[", "{").replace("]", "}").
                                                  replace("{{", "{").replace("}}", "}").replace(": {", ": [{").
                                                  replace("}}", "}]}").replace('}, "timeZone"', '}], "timeZone"'))
                self.__loop_report_dict["insulin_model"] = re.search(r'Optional\((.+?)\(Exponential',
                                                                     dose_store["insulinModel"]).group(1)
                self.__loop_report_dict["action_duration"] = re.search('actionDuration: (.+?), peakActivityTime',
                                                                       dose_store["insulinModel"]).group(1)

            except:
                print("handled error dose store")


        minimed_pump_manager = None
        omnipod_pump_manager = None
        if Sections.MINIMED_PUMP_MANAGER in dict or Sections.OMNIPOD_PUMP_MAANGER in dict:
            if Sections.MINIMED_PUMP_MANAGER in dict:
                try:
                    minimed_pump_manager = dict[Sections.MINIMED_PUMP_MANAGER]
                except:
                    print("handled error minimed pump manager")
            if Sections.OMNIPOD_PUMP_MAANGER in dict:
                try:
                    omnipod_pump_manager = dict[Sections.OMNIPOD_PUMP_MAANGER]
                except:
                    print("handled error omnipod pump manager")

            self.__set_pump_manager_type(minimed_pump_manager, omnipod_pump_manager)

        if Sections.WATCH_DATA_MANAGER in dict:
            try:
                watch_data_manager = dict[Sections.WATCH_DATA_MANAGER]
                self.__loop_report_dict["is_watch_app_installed"] = watch_data_manager["isWatchAppInstalled"].strip()

            except:
                print("handled error watch data manager")

        if Sections.LOOP_DATA_MANAGER in dict:
            try:
                loop_data_manager = dict[Sections.LOOP_DATA_MANAGER]

                self.__loop_report_dict["maximum_basal_rate_per_hour"] = \
                    re.search(r'maximumBasalRatePerHour: Optional\((.+?)\), maximumBolus',
                              loop_data_manager["settings"]).group(1)

                self.__loop_report_dict["maxium_bolus"] = re.search(
                    r'maximumBolus: Optional\((.+?)\), suspendThreshold', loop_data_manager["settings"]).group(1)


                self.__loop_report_dict["retrospective_correction_enabled"] = \
                    re.search('retrospectiveCorrectionEnabled: (.+?), retrospectiveCorrection',
                              loop_data_manager["settings"]).group(1)

                self.__loop_report_dict["suspend_threshold"] = re.search(
                    r'Loop.GlucoseThreshold\(value: (.+?), unit', loop_data_manager["settings"]).group(1)

                """
                self.__loop_report_dict["suspend_threshold_unit"] = re.search(
                    r'"unit": "(.+?)\)\),', self.__loop_data_manager["settings"]).group(1)
    
               
                unable to parse this out currently
                self.__loop_report_dict["workout"] = re.search(
                    '"workout": (.+?)"]], maximumBasalRatePerHour', loop_data_manager["settings"]).group(1)
        
                self.__loop_report_dict["premeal"] = re.search(
                    '"preMeal": (.+?)"]', loop_data_manager["settings"]).group(1)
                """

            except:
                print("handled error loop data manager")



    def __set_pump_manager_type(self, minimed_pump_manager, omnipod_pump_manager):
        if minimed_pump_manager:
            self.__loop_report_dict["pump_manager_type"] = "minimed"
            self.__loop_report_dict["pump_model"] = minimed_pump_manager["pumpModel"].strip()

        elif omnipod_pump_manager:
            self.__loop_report_dict["pump_manager_type"] = "omnipod"
            self.__loop_report_dict["pm_version"] = omnipod_pump_manager["pmVersion"].strip()
            self.__loop_report_dict["pi_version"] = omnipod_pump_manager["piVersion"].strip()

        else:
            self.__loop_report_dict["pump_manager_type"] = "unknown"



