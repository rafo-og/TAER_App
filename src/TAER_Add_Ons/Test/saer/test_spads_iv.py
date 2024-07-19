from .lib.platform import Platform
from .lib.spad_char import SpadChar
from .lib.hp4155A import HP4155A
import csv


class TestSpadsIV(SpadChar):
    def __init__(self) -> None:
        config_path = "chip_configs/config_saer.yaml"
        self.platform = Platform(config_path)
        self.hp4155 = HP4155A()
        # Register parameters
        self.reg_addr = 0x12  # 'REG CHAR' address
        self.signal_col = "char_en_col"
        self.signal_row = "char_en_row"
        self.char_mode = "char_mode"
        # Sweep parameters
        self.Vstart = 0  #   0 V
        self.Vstop = 0.1  # 100 mV
        self.Vstep = 0.001  # 1 mV
        self.Imax = 0.001  # 1 mA
        self.sweep_mode = "MED"
        self.samples = 1  # Number of samples per device
        self.reset()
        self.platform.write_signal(self.char_mode, 1)
        # Disable test pixel
        self.platform.write_fpga_register("SRAM DIV DIN", 0x0F)
        self.platform.app.device.actions.set_aux_signal(1, 1)
        self.platform.app.device.actions.set_aux_signal(1, 0)

    def config(self, Vstart, Vstop, Vstep, Imax, sweep_mode):
        self.Vstart = Vstart
        self.Vstop = Vstop
        self.Vstep = Vstep
        self.Imax = Imax
        self.sweep_mode = sweep_mode

    def __translate_data(self, data):
        data[0].replace("+9.91E+307", "0")
        data[1].replace("+9.91E+307", "0")
        data[2].replace("+9.91E+307", "0")
        data[3].replace("+9.91E+307", "0")
        data[0].replace("\n", "")
        data[1].replace("\n", "")
        data[2].replace("\n", "")
        data[3].replace("\n", "")
        Vk = list(map(float, list(data[0].split(","))))
        Ik = list(map(float, list(data[1].split(","))))
        Va = list(map(float, list(data[2].split(","))))
        Ia = list(map(float, list(data[3].split(","))))
        data = [Vk, Ik, Va, Ia]
        data = list(zip(*data))  # Trasposing
        return data

    def __save_data(self, data, sample, temp):
        n_row = self.get_row().bit_length() - 1
        n_col = self.get_col().bit_length() - 1
        filename = "spads_iv_row" + str(n_row) + "_col" + str(n_col) + "_sample" + str(sample) + ".csv"
        f = open("test/saer/results/spads_iv/" + filename, "w+", newline="")
        w = csv.writer(f, delimiter=";")
        w.writerow(
            [
                "Cathode Voltage",
                "Cathode Current",
                "Anode Voltage",
                "Anode Current",
                "Temperature: " + str(temp),
            ]
        )
        w.writerows(self.__translate_data(data))
        f.close()

    def char_device(self, save=True):
        for sample in range(self.samples):
            data = self.hp4155.sweep_voltage(self.Vstart, self.Vstop, self.Vstep, self.Imax, self.sweep_mode)
            temp = self.platform.app.device.actions.read_adc(0, 0x02)
            if save:
                self.__save_data(data, sample, temp)

    def char_devices(self, row_init=0, samples=1):
        self.samples = samples
        self.sweep_devices(row_init, self.char_device)
