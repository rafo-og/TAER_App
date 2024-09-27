from TAER_Add_Ons.Test.libs.platform import Platform
from TAER_Add_Ons.Test.libs.platform import Platform
from TAER_Add_Ons.Test.libs.spad_char import SpadChar
from TAER_Add_Ons.Test.libs.NP1930C import NP1930

# from TAER_Add_Ons.Test.libs.dso81304b import DSO81304B
# from TAER_Add_Ons.Test.libs.monochrom import Monochromator
import csv
import time
import os
from TAER_Core.Libs import LINK_VALUE_DEF, TRIGGER_DEF
import numpy as np


class TestDelayJitter(SpadChar):
    def __init__(self, bias=None, mode="0.5mA") -> None:
        config_path = "chip_configs/config_saer.yaml"
        bitstream = "test/saer/bitstreams/AER_TOP_rising.bit"
        self.platform = Platform(config_path, bitstream)
        # self.osc = DSO81304B()
        self.osc = None
        # Parameters
        self.__reset_delay()
        self.nbin = 0  # Number of bin
        # Load preset
        if mode == "0.5mA":
            self.platform.load_preset("test/saer/presets/jitter_0.5mA.preset")
        else:
            self.platform.load_preset("test/saer/presets/jitter.preset")

        if bias != None:
            self.platform.write_signal("cfg_delay_bias", bias)

        self.platform.write_fpga_register("PIX_ON ON TIME", 2000000000)
        self.platform.write_fpga_register("PIX_ON PERIOD", 2000000000)

    def __reset_delay(self, mode=0):
        self.platform.app.device.actions.enable_clk_chip(True)
        if mode == 0:
            self.platform.app.device.actions.write_serial(
                [85, 128]
            )  # First byte {2'b10, 6'd21}. Second byte: {2'b10, 6'd0}
        else:
            self.platform.app.device.actions.write_serial(
                [85, 192]
            )  # First byte {2'b10, 6'd21}. Second byte: {2'b11, 6'd0}
        self.platform.app.device.actions.enable_clk_chip(False)

    def __increase_delay(self, inc):
        inc_done = 0
        while inc_done < inc:
            if inc - inc_done > 63:
                inc_delay = 63
            else:
                inc_delay = inc - inc_done
            self.platform.app.device.actions.enable_clk_chip(True)
            spi_data_tx = [85, 64 + inc_delay]
            self.platform.app.device.actions.write_serial(spi_data_tx)
            self.platform.app.device.actions.enable_clk_chip(False)
            inc_done = inc_done + inc_delay
        self.nbin = self.__read_delay_reg()

    def __read_delay_reg(self):
        self.platform.app.device.actions.enable_clk_chip(True)
        self.platform.app.device.actions.write_serial([149, 0, 0, 0])
        time.sleep(0.0002)  # Waiting for RX data to be received
        data_spi = self.platform.app.device.actions.read_serial()
        data_reg_delay = data_spi[3] + (data_spi[2] << 8)
        self.platform.app.device.actions.enable_clk_chip(False)
        print("Next bin: " + str(data_reg_delay))
        return data_reg_delay

    def __meas_data(self, iter):
        self.osc.rst_histogram()
        for i in range(iter):
            self.platform.app.device.actions.start_capture()
            flag_end = self.platform.app.device.actions.is_captured()
            while not flag_end:
                flag_end = self.platform.app.device.actions.is_captured()

    def __save_data(self):
        filename = "bin_" + str(self.nbin)
        self.osc.meas_jitter(filename)

    def __read_data(self):
        [mean, std] = self.osc.meas_results()
        return [mean, std]

    def __save_data(self, out_data):
        filename = "test/saer/results/delay_jitter/delay_jitter.csv"
        if not os.path.exists(filename):
            f = open(filename, "w+", newline="")
            w = csv.writer(f, delimiter=";")
            w.writerow(["Delay", "Jitter", "Bin"])
        else:
            f = open(filename, "a+", newline="")
            w = csv.writer(f, delimiter=";")
        out_data.append(self.nbin)
        w.writerow(out_data)

        # with open("test/saer/results/delay_jitter/delay_jitter.csv", "w+", newline='') as f:
        #     writer = csv.writer(f,  delimiter=';')
        #     writer.writerow(["Delay", "Jitter", "Bin"])
        #     out_data.append(self.nbin)
        #     writer.writerow(out_data)

    def char_delay(self, inc_delay, iter, cap_init=0):
        self.platform.write_signal("ext_res_en", 0)
        self.platform.write_signal("in_bypass", 0)
        self.__reset_delay()
        if cap_init > 0:
            self.__increase_delay(cap_init)
        # out_data = []
        while self.nbin <= 1024:
            self.__meas_data(iter)
            # out_data.append(self.__read_data())
            out_data = self.__read_data()
            self.__save_data(out_data)
            self.__increase_delay(inc_delay)

    def char_nodelay(self, iter):
        self.platform.write_signal("ext_res_en", 0)
        self.platform.write_signal("in_bypass", 1)
        self.__meas_data(iter)
        return self.__read_data()

    def char_window(self, bin_ini=0):
        self.platform.write_signal("ext_res_en", 0)
        self.platform.write_signal("win_bypass", 0)
        self.platform.write_signal("in_bypass", 0)
        self.platform.write_signal("cfg_window_size", 1 << bin_ini)
        self.nbin = bin_ini
        self.platform.write_signal("in_bypass", 1)
        while self.nbin <= 31:
            self.__meas_data(1)
            out_data = self.__read_data()
            self.__save_data(out_data)
            bin_win = self.platform.read_signal("cfg_window_size")
            self.platform.write_signal("cfg_window_size", bin_win << 1)
            self.nbin = self.nbin + 1
            print("Next bin: " + str(self.nbin))
        pass
