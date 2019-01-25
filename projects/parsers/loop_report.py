from .loop_report_parser import parse_loop_report, Sections
import os


class LoopReport:

    def __init__(self, path_and_file_name):
        self.__loop_version = ""
        self.__device_data_manager = ""
        self.__riley_link_device = ""
        self.__path_and_file_name = path_and_file_name
        self.__parse()

    @property
    def loop_version(self):
        return self.__loop_version

    @property
    def device_data_manager(self):
        return self.__device_data_manager

    @property
    def riley_link_device(self):
        return self.__riley_link_device

    def __parse(self):
        dict = parse_loop_report(os.path.realpath(self.__path_and_file_name))
        loop_dict = dict[Sections.LOOP_VERSION]
        self.__loop_version = loop_dict[Sections.LOOP_VERSION]
        self.__device_data_manager = dict[Sections.DEVICE_DATA_MANAGER]
        self.__riley_link_device = dict[Sections.RILEY_LINK_DEVICE]
