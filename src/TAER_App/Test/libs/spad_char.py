# from .platform import Platform UNCOMMENT
from math import log2
import time

# This class controls the SPAD characterization module
class SpadChar:
    def __init__(self) -> None:
        config_path = "chip_configs/config_saer.yaml"
        # self.platform   = Platform(config_path)  # UNCOMMMENT
        # Register parameters
        self.reg_addr = 0x12  # 'REG CHAR' address
        self.signal_col = "char_en_col"
        self.signal_row = "char_en_row"
        self.char_mode = "char_mode"
        # self.reset()

    def __del__(self) -> None:
        self.disable_pixon()

    def reset(self, row_init=0):
        self.__init_row_data()
        self.__update_row_data(row_init)
        self.reg_row = 2**row_init
        self.reg_col = 2**self.col_init
        self.platform.write_signal(self.reg_addr, self.signal_col, self.reg_col)
        self.platform.write_signal(self.reg_addr, self.signal_row, self.reg_row)
        self.platform.write_signal(self.reg_addr, self.char_mode, 1)

    def __init_row_data(self):
        # First column      Last column     Step
        self.info_row_data = [
            [4, 44, 8],  # 50 um
            [4, 44, 8],
            [6, 46, 8],  # 20 um
            [2, 46, 4],
            [3, 47, 4],  # 10 um
            [1, 47, 2],
            [1, 47, 2],  # 5 um
            [0, 47, 1],
            [1, 47, 2],  # 1.85 um
            [0, 47, 1],
            [2, 47, 4],  # Array (cambiar first column por 3 o por 2)
            [2, 47, 4],
            [2, 47, 4],  # Array. Actually, we have a gap every two columns
            [2, 47, 4],
        ]

    def __update_row_data(self, row_init):
        row_data = self.info_row_data[int(row_init)]
        self.col_init = row_data[0]
        self.col_end = row_data[1]
        self.col_step = row_data[2]

    def get_col(self):
        data = self.platform.read_signal(self.reg_addr, self.signal_col)
        return data

    def get_row(self):
        data = self.platform.read_signal(self.reg_addr, self.signal_row)
        return data

    def __shift_col(self):
        flag_end = False
        self.reg_col = self.reg_col << self.col_step
        if self.reg_col > 2**self.col_end:
            flag_end = self.__shift_row()
            row_index = log2(self.get_row())
            self.__update_row_data(row_index)
            self.reg_col = 2**self.col_init
        self.platform.write_signal(self.reg_addr, self.signal_col, self.reg_col)
        return flag_end

    def __shift_row(self):
        flag_end = False
        self.reg_row = self.reg_row << 1
        if self.reg_row > 0x2000:
            self.reg_row = 1
            flag_end = True
        self.platform.write_signal(self.reg_addr, self.signal_row, self.reg_row)
        return flag_end

    def sel_device(self, n_row, n_col):
        if n_row > 13 or n_row < 0 or n_col > 47 or n_col < 0:
            print("ERROR. Row and column number cannot exceed 13 and 47, respectively.")
        else:
            self.platform.write_signal(self.reg_addr, self.signal_col, 2**n_col)
            self.platform.write_signal(self.reg_addr, self.signal_row, 2**n_row)

    def sweep_devices(
        self, row_init, callback
    ):  # callback is the function you want to call when selecting a single device
        flag_end = False
        self.reset(row_init)
        if row_init < 0 or row_init > 13:
            print("ERROR. Initial row must be in the range of 0 to 13.")
            quit()
        else:
            self.reg_row = 2**row_init
            self.__update_row_data(row_init)

        while not flag_end:
            callback()
            flag_end = self.__shift_col()
        pass

    def __reset_array(self):
        self.platform.app.device.actions.enable_clk_chip(True)
        self.platform.app.device.actions.write_spi([19, 4, 255, 19, 4, 100])
        time.sleep(0.001)  # wait reset action
        self.platform.app.device.actions.enable_clk_chip(False)

    def write_sram_global(self, data):
        data = data & 0x0F  # 4 bits
        self.platform.write_fpga_register("SRAM DIV DIN", data)
        self.platform.app.device.actions.set_signal_win0("write_sram", 1)
        self.__reset_array(self)
        self.platform.app.device.actions.set_signal_win0("write_sram", 0)

    def write_sram(self, data):  # Data should be a 64x64 matrix (list of lists)
        data = list(zip(*data))  # now data[i] represents column data

        for i in range(63):  # Writing 63 columns (even rows)
            data_col = data[i][0::2]
            data_col = list(
                map(self.__mask_data, data_col, [0x0F] * len(data_col))
            )  # We avoid the user specifies a value out of range
            self.__write_sram_reg(data_col)

    def __write_sram_reg(self, data_col):
        a = list(map(self.__mask_data, data_col, [0x01] * len(data_col)))
        sram0 = self.__parse_sram_data(data_col, 0)
        sram1 = self.__parse_sram_data(data_col, 1)
        sram2 = self.__parse_sram_data(data_col, 2)
        sram3 = self.__parse_sram_data(data_col, 3)
        # Escribir señales en chip

    def __parse_sram_data(self, data, bit):  # Hay que darl e la vuelta (0 1 1) escr
        col_bits = list(map(self.__mask_data, data, [2**bit] * len(data)))
        col_bits = list(map(lambda x, offset: x >> offset, col_bits, [bit] * len(data)))
        sram_data = 0
        col_bits.reverse()
        for bit in col_bits:
            sram_data = (sram_data << 1) | (bit & 0x01)
        return sram_data

    def __mask_data(self, n, mask):
        return n & mask

    def enable_pixon(self):
        self.platform.app.device.actions.set_signal_win0("pix_on", 1)

    def disable_pixon(self):
        self.platform.app.device.actions.set_signal_win0("pix_on", 1)


if __name__ == "__main__":
    test = SpadChar()
    data = [
        [3, 2, 3],
        [4, 3, 2],
        [3, 2, 3],
        [1, 3, 2],
        [0, 2, 3],
        [7, 3, 2],
    ]
    test.write_sram(data)
