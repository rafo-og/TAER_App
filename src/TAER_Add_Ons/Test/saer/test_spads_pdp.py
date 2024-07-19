from .lib.platform import Platform
from .lib.spad_char import SpadChar
from .lib.NP1930 import NP1930
from .lib.monochrom import Monochromator
import csv
import time
import os
from TAER_Core.Libs import LINK_VALUE_DEF, TRIGGER_DEF
import numpy as np


class TestSpadsPdp(SpadChar):
    def __init__(self, id=1, ndiv=1) -> None:
        config_path = "chip_configs/config_saer.yaml"
        bitstream = "test/saer/bitstreams/AER_TOP.bit"
        self.platform = Platform(config_path, bitstream)
        self.mono = Monochromator()
        self.np1930 = NP1930()
        # Register parameters
        self.reg_addr = 0x12  # 'REG CHAR' address
        self.signal_col = "char_en_col"
        self.signal_row = "char_en_row"
        self.char_mode = "char_mode"
        # Parameters
        self.samples = 1  # Number of samples per device
        self.sphere_factor = 1.022
        self.ndiv = ndiv
        self.reset()
        self.__init_row_data()
        self.set_char_mode(0)
        self.set_lambda(400)
        # Load preset
        self.platform.load_preset("test/saer/presets/DCR.preset")
        self.platform.app.device.actions.write_dac(0x01, 0x01, 500)
        # Counter
        self.cnt_id = id
        # Monochromator
        self.wavelength = 400
        # Disable test pixel
        self.platform.write_fpga_register("SRAM DIV DIN", 0x0F)
        self.platform.app.device.actions.set_aux_signal(1, 1)
        self.platform.app.device.actions.set_aux_signal(1, 0)

    def __init_row_data(self):
        # First column      Last column     Step
        self.info_row_data = [
            [4, 28, 8],  # 0  # 50 um
            [4, 28, 8],
            [6, 30, 8],  # 2  # 20 um
            [2, 14, 4],
            [3, 15, 4],  # 4  # 10 um
            [1, 7, 2],
            [1, 7, 2],  # 6  # 5 um
            [0, 3, 1],
            [1, 7, 2],  # 8  # 1.85 um
            [0, 3, 1],
            [3, 15, 4],  # 10  # Array (cambiar first column por 3 o por 2)
            [3, 15, 4],
            [3, 15, 4],  # Array. Actually, we have a gap every two columns
            [3, 15, 4],
        ]

    def set_lambda(self, wavelength):
        self.wavelength = wavelength
        self.mono.set_lambda(wavelength)
        self.np1930.set_lambda(wavelength)
        power = self.np1930.read_power(samples=10)
        return power

    def __start_counter(self):
        self.platform.app.device.actions.__set_trigger__(
            self.platform.app.device.actions.links.trig_in, TRIGGER_DEF(11)
        )

    def __stop_counter(self):
        self.platform.app.device.actions.__set_trigger__(
            self.platform.app.device.actions.links.trig_in, TRIGGER_DEF(11)
        )

    def __read_counter_data(self):
        data_counts = self.platform.app.device.actions.__read_wire__(0x25, LINK_VALUE_DEF(0, 31))
        data_time = self.platform.app.device.actions.__read_wire__(0x26, LINK_VALUE_DEF(0, 31))
        return [data_counts, data_time]

    def __save_data(self, data_counter):
        n_row = self.get_row().bit_length() - 1
        n_col = self.get_col().bit_length() - 1
        filename = "test/saer/results/spads_pdp/" + "spads_pdp_row" + str(n_row) + ".csv"
        if not os.path.exists(filename):
            f = open(filename, "w+", newline="")
            w = csv.writer(f, delimiter=";")
            w.writerow(
                [
                    "Sample (column)",
                    "Counts",
                    "Clk cycles (12.5 Mhz)",
                    "Integration time",
                    "Mean frequency",
                    "Wavelength",
                    "Optical power",
                ]
            )
        else:
            f = open(filename, "a+", newline="")
            w = csv.writer(f, delimiter=";")

        counts = data_counter[0]
        clk_cycles = data_counter[1]
        t_int = float(clk_cycles) / 100000000
        freq = float(counts / t_int)
        power = self.np1930.read_power(10)

        data_wr = [n_col, counts, clk_cycles, t_int, freq, self.wavelength, power]
        w.writerow(data_wr)
        f.close()

    def char_device(self):
        while self.wavelength <= 1000:
            data_avg = [0, 0]
            for i in range(self.samples):
                self.__start_counter()
                time.sleep(self.tcount)
                self.__stop_counter()
                data = self.__read_counter_data()
                data_avg[0] = data_avg[0] + data[0]
                data_avg[1] = data_avg[1] + data[1]
            self.__save_data(data_avg)
            if self.wavelength < 500:
                inc_lambda = 10
            else:
                inc_lambda = 50
            self.set_lambda(self.wavelength + inc_lambda)
        self.set_lambda(400)
        time.sleep(3)

    def char_devices(self, tcount, samples=1, row_init=0, lambda_init=400):
        self.samples = samples
        self.tcount = tcount
        self.set_lambda(lambda_init)
        self.sweep_devices(row_init=row_init, callback=self.char_device)

    def char_array(self, tcount, samples=1, lambda_init=400, vgate=0):
        self.tcount = tcount
        tcount_raw = int(tcount * 100000000)
        self.platform.app.device.actions.write_dac(0x00, 0x01, vgate)
        self.platform.write_fpga_register("PIX_ON ON TIME", tcount_raw)
        self.platform.write_fpga_register("PIX_ON PERIOD", tcount_raw + 100000)
        self.platform.app.write_dev_register("SRAM DIV DIN", int(7 - np.log2(self.ndiv)))
        self.platform.write_sram_global()
        self.set_lambda(lambda_init)
        while self.wavelength <= 1000:
            img_data_np = np.zeros(4096)
            for i in range(samples):
                img_sample = self.platform.capture()
                print("min: " + str(min(img_sample)) + " max: " + str(max(img_sample)))
                img_data_np = img_data_np + img_sample
            # img_data_np = np.frombuffer(img_data, np.uint32).astype(np.uint16, casting="unsafe")
            power = self.np1930.read_power(10)
            tint = tcount * samples
            data_out = np.append([power, tint, self.ndiv], img_data_np)
            self.__save_data_pdp_array(data_out)
            if self.wavelength < 500:
                inc_lambda = 10
            else:
                inc_lambda = 50
            self.set_lambda(self.wavelength + inc_lambda)

    def __save_data_pdp_array(self, out_data: np.array):
        filename = "test/saer/results/array_pdp/array_pdp_" + str(self.wavelength) + "nm.txt"
        with open(filename, "ab") as f:
            np.savetxt(f, out_data)

    def calib_sphere(self):
        input("Connect the power meter on the left side of the integration sphere and press Enter...")
        power_left = np.array([])
        wavelength = 400
        while wavelength < 1000:
            self.mono.set_lambda(wavelength)
            self.np1930.set_lambda(wavelength)
            power_left = np.append(power_left, self.np1930.read_power(10))
            wavelength = wavelength + 100
        input("Connect the power meter on the top side of the integration sphere and press Enter...")
        power_top = np.array([])
        wavelength = 400
        while wavelength < 1000:
            self.mono.set_lambda(wavelength)
            self.np1930.set_lambda(wavelength)
            power_top = np.append(power_top, self.np1930.read_power(10))
            wavelength = wavelength + 100

        coef = np.divide(power_left, power_top)
        print("Coef (left/top): ")
        print(coef)
        print("Mean : ")
        print(np.mean(coef))

    def meas_dcr_array(self, tcount, samples=1, ndiv=1, vgate=0):
        self.tcount = tcount
        self.ndiv = ndiv
        tcount_raw = int(tcount * 100000000)
        self.platform.app.device.actions.write_dac(0x00, 0x01, vgate)
        self.platform.write_fpga_register("PIX_ON ON TIME", tcount_raw)
        self.platform.write_fpga_register("PIX_ON PERIOD", tcount_raw + 100000)
        self.platform.app.write_dev_register("SRAM DIV DIN", int(7 - np.log2(self.ndiv)))
        self.platform.write_sram_global()
        img_data_np = np.zeros(4096)
        for i in range(samples):
            img_sample = self.platform.capture()
            img_data_np = img_data_np + img_sample * ndiv
            print("min: " + str(min(img_sample)) + " max: " + str(max(img_sample)))
        img_data_np = img_data_np / (tcount * samples)
        self.__save_data_dcr_array(img_data_np)

    def __save_data_dcr_array(self, out_data: np.array):
        filename = "test/saer/results/array_pdp/array_dcr.txt"
        with open(filename, "wb") as f:
            np.savetxt(f, out_data)
