from .lib.platform import Platform
from .lib.spad_char import SpadChar
from .lib.NP1930 import NP1930
from .lib.monochrom import Monochromator
import csv
import time
import os
from TAER_Core.Libs import TRIGGER_DEF, LINK_VALUE_DEF


class TestSpadsDcr(SpadChar):
    def __init__(self, id=1) -> None:
        config_path = "chip_configs/config_saer.yaml"
        bitstream = "test/saer/bitstreams/AER_TOP.bit"
        self.platform = Platform(config_path, bitstream)
        # Register parameters
        self.reg_addr = 0x12  # 'REG CHAR' address
        self.signal_col = "char_en_col"
        self.signal_row = "char_en_row"
        self.char_mode = "char_mode"
        # Parameters
        self.samples = 1  # Number of samples per device
        self.reset()
        self.set_char_mode(0)
        # Load preset
        self.platform.load_preset("test/saer/presets/DCR.preset")
        # Counter
        self.tcount = 1
        self.cnt_id = id
        self.count_1 = 0
        self.time_1 = 0
        # Disable test pixel
        self.platform.write_fpga_register("SRAM DIV DIN", 0x0F)
        self.platform.app.device.actions.set_aux_signal(1, 11)
        self.platform.app.device.actions.set_aux_signal(1, 11)

    def __start_counter(self):
        self.platform.app.device.actions.__set_trigger__(
            self.platform.app.device.actions.links.trig_in, LINK_VALUE_DEF(11)
        )

    def __stop_counter(self):
        self.platform.app.device.actions.__set_trigger__(
            self.platform.app.device.actions.links.trig_in, LINK_VALUE_DEF(11)
        )

    def __read_counter_data(self):
        data_counts = self.platform.app.device.actions.__read_wire__(0x25, LINK_VALUE_DEF(0, 31))
        data_time = self.platform.app.device.actions.__read_wire__(0x26, LINK_VALUE_DEF(0, 31))
        return [data_counts, data_time]

    def __save_data(self, data_counter):
        n_row = self.get_row().bit_length() - 1
        n_col = self.get_col().bit_length() - 1
        filename = "test/saer/results/spads_dcr/" + "spads_dcr_row" + str(n_row) + ".csv"
        if not os.path.exists(filename):
            f = open(filename, "w+", newline="")
            w = csv.writer(f, delimiter=";")
            w.writerow(
                [
                    "Sample (column)",
                    "Counts",
                    "Clk cycles (100 Mhz)",
                    "Integration time",
                    "Mean frequency",
                ]
            )
        else:
            f = open(filename, "a+", newline="")
            w = csv.writer(f, delimiter=";")

        counts = data_counter[0]
        clk_cycles = data_counter[1]
        t_int = float(clk_cycles) / 100000000
        if t_int > 0:
            freq = float(counts / t_int)
        else:
            freq = "NaN"

        data_wr = [n_col, counts, clk_cycles, t_int, freq]
        w.writerow(data_wr)
        f.close()

    def char_device(self):
        data_avg = [0, 0]
        for i in range(self.samples):
            self.__start_counter()
            time.sleep(self.tcount)
            self.__stop_counter()
            data = self.__read_counter_data()
            data_avg[0] = data_avg[0] + data[0]
            data_avg[1] = data_avg[1] + data[1]
        self.__save_data(data_avg)

    def char_devices(self, tcount, samples=1, row_init=0):
        self.samples = samples
        self.tcount = tcount
        self.sweep_devices(row_init, self.char_device)
