from TAER_Core.Libs import Dict2Class
from TAER_Core.main_model import MainModel


class PcbSwitchesModel:
    def __init__(self, base_model: MainModel, config: Dict2Class) -> None:
        self.base_model = base_model
        self.config = config
        self.pcb_switches = {}
        self.__config_signals()

    def __config_signals(self):
        for switch in self.config.pcb_switches.__dict__.values():
            self.pcb_switches[switch.label] = PcbSwitch(switch.label, switch.bit)


class PcbSwitch:
    def __init__(self, label, bit) -> None:
        self.label = label
        self.bit = bit
        self.state = False
