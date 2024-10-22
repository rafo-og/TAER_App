import os
import __main__
from TAER_Core.Libs import Dict2Class
from TAER_Core.main_model import MainModel


class MuxSelectorModel:
    def __init__(self, base_model: MainModel, config: Dict2Class) -> None:
        self.base_model = base_model
        self.config = config
        self.test_signals = {}
        self.__config_signals()

    def __config_signals(self):
        base_model_registers = self.base_model.chip_reg_db.get_item_list()
        for config_signal in self.config.mux_signals.__dict__.values():
            for base_register in base_model_registers.values():
                for base_signal in base_register.signals.values():
                    if config_signal.label == base_signal.label:
                        signal_values = {}
                        for signal_value in config_signal.values:
                            signal_values[signal_value[0]] = signal_value[1]
                        test_signal = TestSignal(
                            config_signal.label,
                            config_signal.caption,
                            base_register,
                            signal_values,
                        )
                        self.test_signals[config_signal.label] = test_signal


class TestSignal:
    def __init__(self, label, caption, reg, values) -> None:
        self.caption = caption
        self.label = label
        self.reg = reg
        self.values = values
