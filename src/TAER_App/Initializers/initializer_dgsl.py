from TAER_App.Initializers.initializer_base import InitializerBase
from TAER_Core.main_model import MainModel
from TAER_Core.Libs import LINK_VALUE_DEF
import numpy as np
import time


class InitializerDGSL(InitializerBase):
    def __init__(self, model: MainModel) -> None:
        super().__init__(model)
        self.chip_name = "digisolar"
        self.controller = DigisolarController(model)
        self.chip_id = 60  # Default value corresponding to CFG_ID = 3'b000
        self.uart_mode = True
        self.aer_mode = False
        self.centroid_radius = (
            5  # Pixels. This value could be dynamically adjusted using 'size' cmd
        )

    """ APP FLOW """

    def on_start_app(self):
        pass

    def on_close_app(self):
        pass

    def on_init_capture(self):
        self.model.device.actions.enable_clk_chip(True)
        self.controller.set_chip_id(self.model.read_dev_register("CFG_UART_ID"))
        self.__set_mode_from_name()
        # Programming internal signals as defined in device registers
        if self.uart_mode:
            self.controller.program_signals()

    def on_before_capture(self):
        # Triggering UART command if required. Note that the timing of internal signals is defined by device registers
        if self.uart_mode:
            if self.aer_mode:
                self.controller.query_action("query_aer")
            else:
                self.controller.query_action("query_cont")

    def on_after_capture(self, raw_data):
        """The interface enters this state once 'frame_done' or 'events_done' is received. Thus, this state occurs after 'T_FRAME' in UART mode"""
        if self.model.FR_raw_mode_en:  # Note that this is only possible in AER (FPGA/Events)
            self.model.main_img_data = self.reconstruct_events()
        elif self.uart_mode:  # Here we have to wait until we receive the RX Frame
            if self.aer_mode:
                x_c, y_c = self.controller.read_uart_aer()
            else:
                x_c, y_c = self.controller.read_uart_cont()
            self.draw_centroid(x_c, y_c, self.centroid_radius)
        elif self.aer_mode:  # AER (FPGA/Frame)
            self.model.main_img_data = raw_data
        else:  # Continuos (FPGA) mode
            y_c, x_c = self.read_centroid_fpga()
            self.draw_centroid(x_c, y_c, self.centroid_radius)

        addr_rd, addr_wr = self.model.device.actions.check_addr_ram()

        print("Read: " + str(addr_rd) + " Write: " + str(addr_wr))

    def on_end_capture(self):
        self.model.device.actions.enable_clk_chip(False)
        pass

    def on_test(self):
        # UNCOMMENT TO CHECK SPOT SIZE
        self.controller.query_action("size")
        s_x, s_y = self.controller.read_data("size")
        self.model.logger.info("The spot has: " + str(s_y) + " rows and " + str(s_x) + " cols")
        # UNCOMMENT TO CHECK TEMPERATURE
        self.controller.query_action("temp")
        time.sleep(0.001)  # Wait for Temp. sensor to convert. INCREASE IF REQUIRED
        t_temp, t_ref = self.controller.read_data("temp")
        T = t_ref / t_temp
        self.model.logger.info(
            "Temperature: "
            + str(T)
            + ". Check whether 'T' is properly computed. You may need to add a constant to convert the value into ºC or K."
        )

    """ UART COMM """

    def gen_serial_frame(self, mode, register):
        self.model.device.actions.enable_clk_chip(True)
        bytes_tx = self.controller.gen_tx_packet(
            mode, register.address, register.value
        )  # Even when we read, we send the register value, as it is ignored
        return bytes_tx

    def parse_serial_frame(self, serial_data, register: None):
        if serial_data is not None:
            data_rx = self.controller.parse_rx_data("read", serial_data)
        else:
            data_rx = list([])
        return data_rx

    """ FPGA METHODS"""

    def read_centroid_fpga(self):
        centroid = self.model.device.actions.__read_wire__(0x24, LINK_VALUE_DEF(0, 31))
        x_c = centroid & (2**16 - 1)
        y_c = centroid >> 16
        return y_c, x_c

    def en_power_supply(self, domain: str, mode):
        """This function turns on/off a power domain.
        -domain must be "1.8" or "3.3" (string)
        -mode: True or False"""
        if domain == "1.8":
            switch_bit = 0
        elif domain == "3.3":
            switch_bit = 1
        self.model.device.actions.set_pcb_switch(switch_bit, mode)

    """" MISC. """

    def __set_mode_from_name(self):
        mode_name = self.model.get_current_mode_name(self.model.current_mode)
        if mode_name == "AER (FPGA/Events)":
            self.model.FR_raw_mode_en = True
        else:
            self.model.FR_raw_mode_en = False

        if mode_name == "Continuous (UART)" or mode_name == "AER (UART)":
            self.uart_mode = True
        else:
            self.uart_mode = False

        if mode_name == "AER (FPGA/Events)" or mode_name == "AER (UART)" or mode_name == "AER (FPGA/Frames)":
            self.aer_mode = True
        else:
            self.aer_mode = False

    def reconstruct_events(self, raw_data):
        im_out = np.zeros([384, 384])
        addresses = raw_data[0::2]
        for x in range(384):
            for y in range(384):
                addr_pix = (y << 16) + x
                im_out[y, x] = np.sum(addresses == addr_pix)
        return im_out

    def draw_centroid(self, x_c, y_c, radius):
        img = np.zeros((384, 384))
        if (x_c > 0) & (y_c > 0):
            self.model.logger.info("Centroid: (" + str(y_c) + ", " + str(x_c) + ").")
            for i in range(img.shape[0]):
                for j in range(img.shape[1]):
                    # Calculate the distance between the current pixel and the center of the circle
                    distance = np.sqrt((i - x_c) ** 2 + (j - y_c) ** 2)
                    # If the distance is less than or equal to the radius, set the pixel value to 255
                    if round(distance) <= radius:
                        img[i, j] = 255
        else:
            self.model.logger.warning(
                "Centroid not found. Check timing of control signals and threshold voltage."
            )
        self.model.main_img_data = img

    def save_image(self, data_in, path):
        with open(path, "ab") as f:
            np.savetxt(f, data_in)


class DigisolarController:
    def __init__(self, model: MainModel) -> None:
        self.chip_id = 60
        self.model = model

    def set_chip_id(self, cfg_id):
        self.chip_id = 60 + cfg_id

    def gen_tx_packet(self, mode, addr_reg=None, data_tx=0):
        packet_tx = DigisolarPacket()
        bytes_tx = packet_tx.gen_tx_bytes(self.chip_id, mode, addr_reg, data_tx)
        return bytes_tx

    def parse_rx_data(self, mode, bytes_rx):
        if len(bytes_rx):
            packet_rx = DigisolarPacket(bytes_rx)
            data_rx = packet_rx.parse_rx_data(mode)
        else:
            self.model.logger.error("ERROR: no RX data")
        return data_rx

    def query_action(self, action: str):
        """This function triggers the operation of the sensor. The function 'read_data' must be used to read the RX after the execution time.

        Args:
            action (str): Options are 'query_aer', 'query_cont', 'size', 'temp'.
        """
        bytes_tx = self.gen_tx_packet(action)
        self.model.device.actions.write_serial(bytes_tx)

    def read_data(self, action: str):
        bytes_rx = self.model.device.actions.read_serial()
        if bytes_rx is not None:
            data = self.parse_rx_data(action, bytes_rx)
        else:
            data = list([])
        return data

    def program_signals(self):
        pixon_on = list(self.model.read_dev_register("T_EXP").to_bytes(4, "little"))
        pixon_del = list(self.model.read_dev_register("T_EN_DELAY").to_bytes(4, "little"))
        rstregs_on = list(self.model.read_dev_register("T_RSTREGS_ON").to_bytes(4, "little"))
        rstregs_del = list(self.model.read_dev_register("T_RSTREGS_DEL").to_bytes(4, "little"))
        rstperiph_on = list(self.model.read_dev_register("T_RSTPERIPH_ON").to_bytes(4, "little"))
        self.model.write_signal("cfg_sgnl_width_pixon<0>", pixon_on[0])
        self.model.write_signal("cfg_sgnl_width_pixon<1>", pixon_on[1])
        self.model.write_signal("cfg_sgnl_width_pixon<2>", pixon_on[2])
        self.model.write_signal("cfg_sgnl_width_pixon<3>", pixon_on[3])
        self.model.write_signal("cfg_sgnl_width_rstperiph<0>", rstperiph_on[0])
        self.model.write_signal("cfg_sgnl_width_rstperiph<1>", rstperiph_on[1])
        self.model.write_signal("cfg_sgnl_width_rstperiph<2>", rstperiph_on[2])
        self.model.write_signal("cfg_sgnl_width_rstperiph<3>", rstperiph_on[3])
        self.model.write_signal("cfg_sgnl_width_rstregs_n<0>", rstregs_on[0])
        self.model.write_signal("cfg_sgnl_width_rstregs_n<1>", rstregs_on[1])
        self.model.write_signal("cfg_sgnl_width_rstregs_n<2>", rstregs_on[2])
        self.model.write_signal("cfg_sgnl_width_rstregs_n<3>", rstregs_on[3])
        self.model.write_signal("cfg_sgnl_delay_pixon<0>", pixon_del[0])
        self.model.write_signal("cfg_sgnl_delay_pixon<1>", pixon_del[1])
        self.model.write_signal("cfg_sgnl_delay_pixon<2>", pixon_del[2])
        self.model.write_signal("cfg_sgnl_delay_pixon<3>", pixon_del[3])
        self.model.write_signal("cfg_sgnl_delay_rstregs_n<0>", rstregs_del[0])
        self.model.write_signal("cfg_sgnl_delay_rstregs_n<1>", rstregs_del[1])
        self.model.write_signal("cfg_sgnl_delay_rstregs_n<2>", rstregs_del[2])
        self.model.write_signal("cfg_sgnl_delay_rstregs_n<3>", rstregs_del[3])

    def read_uart_aer(self):
        data_rx = self.read_data("query_aer")
        if len(data_rx) == 3:
            x_s = data_rx[0]
            y_s = data_rx[1]
            n = data_rx[2]
            if n > 0:
                x_c = x_s / n
                y_c = y_s / n
            else:
                y_c = 0
                x_c = 0
        else:
            x_c = 0
            y_c = 0
            self.model.logger.error(
                "Wrong RX data frame. Check TX data frame and make sure that 'T_FRAME' is long enough and 'T_FRAME > T_EXP'"
            )
        return x_c, y_c

    def read_uart_cont(self):
        data = self.read_data("query_cont")
        if len(data) == 2:
            x_c = (data[0] >> 1) + (data[0] & 1) * 0.5  # LSB corresponds to 0.5 pixels
            y_c = (data[1] >> 1) + (data[1] & 1) * 0.5  # LSB corresponds to 0.5 pixels
        else:
            x_c = 0
            y_c = 0
            self.model.logger.error(
                "Wrong RX data frame. Check TX data frame and make sure that 'T_FRAME' is long enough and 'T_FRAME > T_EXP'"
            )
        return x_c, y_c


class DigisolarPacket:
    def __init__(self, bytes_rx=None) -> None:
        if bytes_rx == None:
            self.addr = 60
            self.cmd = 0x00
            self.len = 2
            self.data = list([0])
            self.errcode = 0
            self.chk = (self.addr + self.cmd + self.len + self.data[0]) & 0xFF
        else:
            self.addr = bytes_rx[0]
            self.cmd = bytes_rx[1]
            self.len = bytes_rx[2]
            if self.cmd == 0x41:  # BUG IN HARDWARE: 'CMD_SIZE' returns 6 instead of 4
                self.len = 4
            self.data = list(bytes_rx[3 : 3 + self.len - 2])  # LENGTH -ERRRCODE -CHEKCUSM
            self.errcode = bytes_rx[3 + self.len - 2]
            self.chck = bytes_rx[3 + self.len - 1]

    def gen_tx_bytes(self, addr, mode, addr_reg=None, data=0):
        """Generates TX data frame from input data.

        Args:
            addr (byte): UART ID ranging from 60 to 67.
            mode (str): String indicating the mode. Valid values: "write", "read", "query_aer", "query_cont", "size", "temp".
            addr_reg (bye): Optional. Address of register to be read/written in "write" or "read" mode.
            data (list of bytes): Data to be transmitted in APP DATA field

        Returns:
            bytes_tx: list of bytes to be sent to serial interface
        """
        self.addr = addr & 0xFF
        if mode == "write":
            self.cmd = addr_reg | 2**7
        elif mode == "read":
            self.cmd = addr_reg
        elif mode == "query_cont" or mode == "query_aer":
            self.cmd = 0x40
        elif mode == "size":
            self.cmd = 0x41
        elif mode == "temp":
            self.cmd = 0x42
        self.len = len(data.to_bytes(1, "little")) + 1  # + Checksum
        self.data = list(data.to_bytes(1, "little"))  # Note that in this impllementation APP is alwaays 1-byte long
        self.gen_checksum()
        bytes_tx = (
            list([self.addr, self.cmd, self.len]) + self.data + list([self.chk])
        )  # List of bytes to be sent: | ADDR | CMD | LEN | DATA | CHK |
        return bytes_tx

    def parse_rx_data(self, mode):  # List of bytes received: | ADDR | CMD | LEN | DATA(LEN) | ERR CODE | CHK |
        """Generates RX data from RX bytes.

        Args:
            mode (str): String indicating the mode. Valid values: "write", "read", "query_aer", "query_cont", "size", "temp".

        Returns:
            data (list of int): Data received from the sensor.
        """
        data = list([])
        if len(self.data):  # Check if empty
            if mode == "write":
                data.append(int.from_bytes(self.data, "little"))
            elif mode == "read":
                data = int.from_bytes(self.data, "little")
            elif mode == "query_cont" or mode == "temp":
                data.append(int.from_bytes(self.data[0:2], "little"))
                data.append(int.from_bytes(self.data[2:4], "little"))
            elif mode == "query_aer":
                data.append(int.from_bytes(self.data[0:4], "little"))
                data.append(int.from_bytes(self.data[4:8], "little"))
                data.append(int.from_bytes(self.data[8:12], "little"))
            elif mode == "size":
                data = self.data
            else:
                data = -1
        return data

    def gen_checksum(self):
        self.chk = (self.addr + self.cmd + self.len + sum(self.data)) & 0xFF

    def check_checksum(self):
        chk_ideal = (self.addr + self.cmd + self.len + self.data) & 0xFF
        return self.chk == chk_ideal
