from .hp4155A import HP4155A
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.__file__)))))
from main_model import MainModel
from Libs.config import Config


class Platform:
    def __init__(self, config_path) -> None:
        Config.CONFIG_PATH = config_path
        self.app = MainModel()
        self.__config_model()
        self.app.device.start()
        self.__check_device()
        self.__load_bitstream()

    def __config_model(self):
        self.app.config()

    def __check_device(self):
        if not (self.app.device.is_connected):
            print("ERROR. Please, connect the device before launching the script.")
            quit()

    def __load_bitstream(self):
        self.app.device.program("test/saer/bitstreams/AER_TOP.bit")
        print("Bitstream loaded.")

    def read_signal(self, address, signal):
        self.app.read_registers_chip()

        reg_list = self.app.registers_chip_list
        reg_id = reg_list.get_id(address=address)
        reg = reg_list.get_chip_value()[reg_id]
        sig_id = reg.get_id(signal)
        data = reg.get_signal(sig_id)

        return data

    def write_signal(self, address, signal, value):
        reg_list = self.app.registers_chip_list
        reg_id = reg_list.get_id(address=address)
        reg = reg_list.get_chip_value()[reg_id]
        sig_id = reg.get_id(signal)
        self.app.write_registers_chip(sig_id, value)

    def write_fpga_register(self, label, value):
        reg_list = self.app.registers_device_list
        reg_list.set_value(value, label)
        self.app.device.write_registers(reg_list.get_chip_value())


if __name__ == "__main__":
    config_path = "chip_configs/config_saer.yaml"
    test = Platform(config_path)
    print(test.read_signal(0x02, "cfg_delay_bias"))
    test.write_signal(0x02, "cfg_delay_bias", 5)
    print(test.read_signal(0x02, "cfg_delay_bias"))
