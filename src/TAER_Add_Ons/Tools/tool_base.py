import sys
import itertools
import os
from TAER_Core.Libs import ModelConfig
from TAER_Core.Libs import Config, Dict2Class


class ToolBase:
    id_iter = itertools.count()

    def __init__(self, name):
        self.id = next(ToolBase.id_iter)
        self.name = name
        config = ModelConfig()
        for tool in config.tools:
            if self.name == tool[0]:
                self.is_enabled = tool[1]
                self.chip_reg_update = tool[2]
                self.dev_reg_update = tool[3]
                break
            else:
                self.is_enabled = False
                self.chip_reg_update = False
                self.dev_reg_update = False
        self.__config_tool(config.chip_name)

    def __config_tool(self, chip_name):
        tool_folder_name = str.lower(self.name).replace(" ", "_")
        # Check if the application has been frozen to executable file
        if getattr(sys, "frozen", False):
            main_path = os.path.dirname(sys.executable)
        else:
            main_path = os.path.dirname(__file__)
            main_path = os.path.join(main_path, "..")
        config_path = os.path.join(main_path, "chip_configs", "Tools", tool_folder_name)
        config_filepaths = os.listdir(config_path)
        for file in config_filepaths:
            config_filepath = os.path.join(config_path, file)
            if config_filepath != os.path.join(config_path, "config_template.yaml"):
                config = Config(config_filepath)
                config_dict = Dict2Class(config.value["TOOL"])
                if config_dict.chip_name == chip_name:
                    self.config = config_dict
                    break
                else:
                    self.config = None
        if self.config is None:
            config_filepath = os.path.join(config_path, "config_template.yaml")
            if not os.path.exists(config_path):
                raise Exception(f"{tool_folder_name} tool configuration not found on {config_path}.")
            config = Config(config_filepath)
            self.config = Dict2Class(config.value["TOOL"])

    def open(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

    def update_view(self):
        raise NotImplementedError

    def is_shown(self):
        raise NotImplementedError
