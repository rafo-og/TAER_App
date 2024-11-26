import os
import warnings
import time
import pickle
from typing import Callable
import numpy as np
import cv2 as cv
from datetime import date
from TAER_Core.main_model import MainModel, ChipRegister
from TAER_Core.Libs import LINK_VALUE_DEF, TRIGGER_DEF
from TAER_App.Initializers.initializer_base import InitializerBase
from TAER_App.Test.scp.GetDataset import DataSetGatheringPresenter
from TAER_App.Test.scp.Consumption import ConsumptionTest
from TAER_App.Test.scp.LightResponse import LightResponse

onedrive_path = os.getenv("OneDrive")
datetime = date.today().strftime("%d_%m_%Y")
tmp_folder = os.path.join(
    onedrive_path, f"Thesis/SCP/TEST/EXPERIMENTS/tmp/TAER/{datetime}"
)


class InitializerSCP(InitializerBase):
    def __init__(self, model: MainModel) -> None:
        super().__init__(model)
        self.getDataSetApp = None
        self.chip_name = "chip_scp"
        self.current_raw_data = None

    def on_start_app(self):
        pass

    def on_close_app(self):
        pass

    def on_init_capture(self):
        self.__set_mode_from_name()
        self.__set_signals_from_modelname()

    def on_before_capture(self):
        if self.__check_mode("SC AER SEQ"):
            self.model.device.actions.enable_clk_chip(True)
        else:
            self.model.device.actions.enable_clk_chip(False)

    def on_after_capture(self, raw_data):
        # self.logger.info("Processing image...")
        save_images = False
        if self.__check_mode("SC AER SEQ"):
            self.model.device.actions.enable_clk_chip(False)
        if save_images:
            self.__save_raw_img(raw_data, os.path.join(tmp_folder, "data_raw.bin"))
        if not (self.model.TFS_raw_mode_en or self.model.FR_raw_mode_en):
            self.model.main_img_data = raw_data
            self.logger.info(f"Events FR: {np.sum(raw_data)}")
        elif self.model.FR_raw_mode_en and self.__check_mode("SC AER SEQ"):
            raw_data = self.decode_seq_data(raw_data)
            sc_img, _ = self.__sc_compute(raw_data, self.__sc_michelson)
            self.model.main_img_data = self.build_sc_image(sc_img)
        elif self.model.FR_raw_mode_en and not self.__check_mode("Raw mode (SCP)"):
            self.current_raw_data = raw_data
        elif self.__check_mode("Raw mode (SCP)(TH)"):
            # sc_img = self.__sc_compute(raw_data, self.__sc_lenero)
            # sc_img = self.__sc_compute(raw_data, self.__sc_weber)
            sc_img, _ = self.__sc_compute(raw_data, self.__sc_michelson)
            sc_img_th = np.copy(sc_img)
            sc_img_th[sc_img <= 0.08] = 255
            sc_img_th[sc_img > 0.08] = 0
            sc_img_th = sc_img_th.reshape((-1,))
            # sc_img = self.__remove_cluster_effects(sc_img)
            sc_img = sc_img.reshape((-1,))
            self.model.main_img_data = sc_img_th
        else:
            # sc_img = self.__sc_compute(raw_data, self.__sc_lenero)
            # sc_img = self.__sc_compute(raw_data, self.__sc_weber)
            self.control_vth(raw_data)
            sc_img, _ = self.__sc_compute(raw_data, self.__sc_michelson)
            # sc_img = self.__remove_cluster_effects(sc_img)
            self.model.main_img_data = self.build_sc_image(sc_img)
        # self.logger.info("Processing image... Done.")

    def on_end_capture(self):
        if self.model.FR_raw_mode_en and not self.__check_mode("Raw mode (SCP)"):
            img_pre = self.process_fr_raw_counts(self.current_raw_data[0 : (2**16)])
            self.model.main_img_data = img_pre

    def on_test(self):
        # self.get_img_dataset()
        # self.check_fsm_fifo_readout()
        # self.consumption_tool()
        self.light_response()

    def gen_serial_frame(self, operation: str, register: ChipRegister):
        """Generate the SPI data frame to send depending on several parameters

        Args:
            operation (str): It could be \"write\" or \"read\"
            mode (int): It represents different protocols to communicate with the chip over SPI.
            Currently, only mode 1 and mode 2 are defined.
            register (ChipRegister): An object with all the data related with the register properties

        Returns:
            numpy array: The data frame to send over SPI
        """
        # The default operation consists of a SPI interface that sends the address
        # of the register to be written. MSB = 1 for writting.
        # E.g.: Writing 0x3C to register 0x17 -> TX = {0x17 | 0x80, 0x3C}
        # E.g.: Reading register 0x17 -> TX = {0x17, 0x3C}
        self.model.device.actions.enable_clk_chip(True)
        data = None
        if operation == "write":
            data = [(register.address & 0x7F) | 0x80, register.value]
        elif operation == "read":
            data = [(register.address & 0x7F), 0]
        else:
            self.logger.error("Operation not allowed.")
        return data

    def parse_serial_frame(self, data: list, register: ChipRegister) -> list:
        """Parse the incoming data from SPI depending on several parameters

        Args:
            data (list): The data to parse
            mode (int): It represents different protocols to communicate with the chip over SPI.
            Currently, only mode 1 and mode 2 are defined.
            register (ChipRegister): An object with all the data related with the register properties

        Returns:
            list: The parsed data
        """
        # The default operation consists of a SPI interface that returns the register
        # value after receiving the address in the first byte
        # E.g.: Reading register 0x17 -> TX = {0x17, 0x00} -> RX = {0x00, DATA}
        self.model.device.actions.enable_clk_chip(False)
        if len(data) > 1:
            return data[1]
        else:
            return []

    def __set_mode_from_name(self):
        if self.__check_mode("Raw mode (SCP)") or self.__check_mode(
            "Raw mode (SCP)(TH)"
        ):
            self.model.TFS_raw_mode_en = True
            self.model.FR_raw_mode_en = False
        elif self.__check_mode("Raw mode (FR)"):
            self.model.TFS_raw_mode_en = False
            self.model.FR_raw_mode_en = True
        elif self.__check_mode("SC AER SEQ"):
            self.model.TFS_raw_mode_en = False
            self.model.FR_raw_mode_en = True
        else:
            self.model.TFS_raw_mode_en = False
            self.model.FR_raw_mode_en = False

    def __set_signals_from_modelname(self):
        self.__set_cfg_signal(EXT_SIG.RST_CLUSTER_BIT0, 0)
        self.__set_cfg_signal(EXT_SIG.RST_CLUSTER_BIT1, 0)
        self.__set_cfg_signal(EXT_SIG.AER_RST_SRC, 1)
        self.__set_cfg_signal(EXT_SIG.AER_REQ_SRC, 1)
        if self.__check_mode("SC AER SEQ"):
            self.__set_cfg_signal(EXT_SIG.SENSOR_CTRL_CFG, 1)
            self.__set_cfg_signal(EXT_SIG.PAR_IFACE_SRC, 1)
            self.__set_cfg_signal(EXT_SIG.PAR_IFACE_PAD_CFG, 1)
        else:
            self.__set_cfg_signal(EXT_SIG.PAR_IFACE_PAD_CFG, 0)
            self.__set_cfg_signal(EXT_SIG.SENSOR_CTRL_CFG, 0)
            self.__set_cfg_signal(EXT_SIG.PAR_IFACE_SRC, 0)
        self.model.device.actions.__update_wires__()

    def __sc_compute(
        self, raw_data: np.ndarray, method: Callable[[int, int], float]
    ) -> np.ndarray:
        """Process raw data from SC sensor running in Spatial Contrast mode.

        Args:
            raw_data (np.ndarray): An array containing the raw data.
            method (Callable[[int, int], float]): The method to use to process the
                                                contrast (i.e. sc_michelson).

        Returns:
            np.ndarray: The processed image.
        """
        mapping1, mapping2, res = self.process_scp_times(raw_data)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            scp = method(mapping1, mapping2)
            # Sometimes the second spike is not triggered resulting in a negative contrast
            # t2 == 0 and t1 > 0
            scp[scp < 0] = 0
        scp = scp.reshape(-1, 1)
        if len(np.isnan(scp)):
            print("There are NaN values in computed image, replacing by zero...")
            scp[np.isnan(scp)] = 0
        return scp, res

    def process_scp_times(self, raw_data: np.ndarray):
        res = True
        address = raw_data[0::2]
        times = raw_data[1::2]
        # Get the two frames (first and second spike)
        t1 = np.zeros((128, 128))
        t2 = np.zeros((128, 128))
        data_errors = np.zeros((128, 128))
        for i in np.arange(0, len(address)):
            x = address[i] & 0xFFFF
            y = (address[i] >> 16) & 0xFFFF
            if x > 127 or y > 127:
                print(f"{i}: {times[i]} || {x}, {y}")
                res = False
                break
            else:
                if t1[x, y] == 0:
                    t1[x, y] = times[i]
                elif t2[x, y] == 0:
                    t2[x, y] = times[i]
                else:
                    data_errors[x, y] = data_errors[x, y] + 1
                    if data_errors[x, y] > 2:
                        print(
                            f"Pixel ({x}, {y}) triggers {data_errors[x, y] + 1} events."
                        )
                    dt1 = t2[x, y] - t1[x, y]
                    dt2 = times[i] - t2[x, y]
                    if dt1 < dt2:
                        t2[x, y] = times[i]
        return t1, t2, res

    def decode_seq_data(self, raw_data: np.ndarray):
        onfile = False
        global_shutter = self.model.read_signal("o_cfg_reset_pix_mode")
        cluster = 0
        if onfile:
            filepath = "./tmp/data_seq.log"
            if os.path.exists(filepath):
                os.remove(filepath)
            f = open(filepath, "a")
        tm = 0
        t = 0
        terrors = 0
        dev_data = []
        sel_frame_flag = None
        for data in raw_data:
            data_type_flag = (data >> 15) & 0x01
            if data_type_flag:
                tm = data & 0x7FFF
                if tm < t:
                    if onfile:
                        f.write(f"--> ---- TIME {tm} ---- \t {'{0:015b}'.format(tm)}\n")
                        terrors += 1
                else:
                    if onfile:
                        f.write(f"--- TIME {tm} ---- \t\t\t {'{0:015b}'.format(tm)}\n")
                t = tm
            else:
                y = (data >> 8) & 0x7F
                x = data & 0x7F
                frame_flag = (data >> 7) & 0x01
                if onfile:
                    f.write(f"{frame_flag}\t|\t{x}\t|\t{y}\n")
                if sel_frame_flag is None:
                    sel_frame_flag = frame_flag
                if sel_frame_flag != frame_flag:
                    if global_shutter:
                        self.logger.warning("Next frame detected.")
                        break
                    else:
                        t = 0
                        sel_frame_flag = frame_flag
                        cluster += 1
                        if cluster == 4:
                            break
                addr = np.left_shift(y, 16) | x
                dev_data.append(addr)
                dev_data.append(tm)
        if onfile:
            f.close()
        if terrors:
            self.logger.warning(f"Total timestamp errors {terrors}")
        return np.array(dev_data)

    def control_vth(self, raw_data: np.ndarray):
        max_vth = 28  # Maximum Vth
        min_vth = 10  # Minimum Vth
        texp = self.model.read_dev_register("T_PIXON")  # Get the exposure time
        ttol = [100000, 200000]  # Set a windows for the last event
        vth = self.model.read_signal("o_wreg_dac_vth<4:0>")  # Read the current vth
        last_event = raw_data[-1]  # Get the last event time
        ndata = len(raw_data)
        dataperframe = 65536
        if ndata < dataperframe:  # The matrix has not triggered entirely
            if vth < max_vth:  # Increase Vth if lower than the maximum
                vth = vth + 1
                self.model.write_signal("o_wreg_dac_vth<4:0>", vth)
        elif last_event < (texp - ttol):  # The last event occurred much time before
            if vth > min_vth:  # the total exposure time
                vth = vth - 1  # Decrease Vth if higher than minimum
                self.model.write_signal("o_wreg_dac_vth<4:0>", vth)
        self.logger.info(f"Vth {vth}")

    # Contrast methods
    def __sc_lenero(self, t1, t2):
        return 1 - t1 / t2

    def __sc_weber(self, t1, t2):
        return np.linalg.norm(t2 / t1 - 1, keepdims=True)

    def __sc_michelson(self, t1, t2):
        return (t2 - t1) / (t1 + t2)

    def build_sc_image(self, value):
        # sc_img = sc_img.reshape((-1,))
        # sc_img[sc_img > 0] = np.log10(sc_img[sc_img > 0] * 1000)
        # sc_img = -sc_img
        # sc_img = sc_img - sc_img.min()
        vmin = value.min()
        vmax = value.max()
        if vmax - vmin > 0:
            value = (value - vmin) / (vmax - vmin) * 255
        value = value.astype("uint8")
        value = value.reshape((self.model.config.img.w, self.model.config.img.h))
        value = cv.applyColorMap(value, cv.COLORMAP_HOT)
        return value

    # Image correction methods
    def __remove_cluster_effects(self, img):
        img[:, 63] = img[:, 61]
        img[:, 62] = img[:, 61]
        img[:, 64] = img[:, 66]
        img[:, 65] = img[:, 66]
        img[63, :] = img[61, :]
        img[62, :] = img[61, :]
        img[64, :] = img[66, :]
        img[65, :] = img[66, :]
        return img

    # Auxiliar methods
    def __save_raw_img(self, img, filename):
        filename = self.__create_new_filename(filename)
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            img.tofile(f)  # To recover the info use fromfile function

    def process_fr_raw_counts(self, raw_data):
        im_out = np.zeros([self.model.config.img.w, self.model.config.img.h])
        addresses = raw_data[0::2]
        for x in range(self.model.config.img.w):
            for y in range(self.model.config.img.h):
                addr_pix = (y << 16) + x
                im_out[x, y] = np.sum(addresses == addr_pix)
        return im_out

    def process_fr_raw_periods(self, raw_data):
        im_out = np.zeros([self.model.config.img.w, self.model.config.img.h])
        addresses = raw_data[0::2]
        times = raw_data[1::2]
        for x in range(self.model.config.img.w):
            for y in range(self.model.config.img.h):
                addr_pix = (y << 16) + x
                times_pix = times[np.where(addresses == addr_pix)]
                if len(times_pix) > 2:
                    im_out[x, y] = 1 / (
                        np.median(times_pix[1:] - times_pix[0:-1]) * 1e-6
                    )
                else:
                    im_out[x, y] = 0
        return im_out

    def __check_mode(self, mode):
        mode_name = self.model.get_current_mode_name(self.model.current_mode)
        if mode == mode_name:
            return True
        else:
            return False

    def __create_new_filename(self, path):
        mode_name = self.model.get_current_mode_name(self.model.current_mode)
        mode_name = mode_name.replace(" ", "_")
        filename, extension = os.path.splitext(path)
        filename = filename + mode_name
        path = filename + extension
        counter = 1
        while os.path.exists(path):
            path = filename + "_" + str(counter) + extension
            counter += 1
        return path

    # Configuration methods
    def __set_cfg_signal(self, signal, value):
        self.model.device.actions.__set_wire__(
            self.model.device.actions.links.win0, value, signal
        )

    def load_preset(self, preset):
        with open(preset, "rb") as fp:
            to_load = pickle.load(fp)
        if to_load is not None:
            self.model.set_preset(to_load)

    # Test methods
    def get_img_dataset(self):
        self.getDataSetApp = DataSetGatheringPresenter(self.model)
        self.getDataSetApp.start()

    def consumption_tool(self):
        self.measTool = ConsumptionTest(self.model)
        self.measTool.start()

    def check_fsm_fifo_readout(self):
        PRESET_PATH = os.path.join(
            onedrive_path, "Thesis/SCP/TEST/PRESETS/scp_seq_v4.preset"
        )
        fifo_data_in = np.arange(10, 200)
        flag = 1
        self.model.device.actions.enable_clk_chip(False)
        time.sleep(1)
        # ----------- RESET FPGA MODULES ----------
        self.model.device.actions.stop_capture()
        self.model.device.actions.reset_fifo()
        self.model.device.actions.reset_ram()
        self.model.device.actions.reset_aer()
        # ----------- RESET CHIP ------------------
        self.model.device.actions.reset_chip()
        time.sleep(1)
        # ------ CONFIGURE SENSOR AND FPGA --------
        self.model.device.actions.enable_clk_chip(True)
        self.load_preset(PRESET_PATH)
        self.on_init_capture()
        time.sleep(1)
        # ------ LOAD VALUES IN FIFO --------------
        for data in fifo_data_in:
            self.model.write_signal("o_wreg_to_fifo_test<7:0>", int(data & 0xFF))
            self.model.write_signal(
                "o_wreg_to_fifo_test<15:0>", int((data >> 8) & 0xFF)
            )
            self.model.write_signal("o_write_fifo_flag_test", flag)
            if flag:
                flag = 0
            else:
                flag = 1
        # ---- READ FIFO WITH INTERNAL FSM ------
        self.model.device.actions.events_done()
        n_events = (self.model.read_dev_register("N_EVENTS") // 4) * 32
        self.model.device.actions.start_capture()
        time.sleep(1)
        self.model.write_signal("o_start_fsm_readout", 1)
        time.sleep(1)
        self.model.write_signal("o_start_fsm_readout", 0)
        time.sleep(1)
        flag = self.model.device.actions.events_done()
        self.model.device.actions.stop_capture()
        if not flag:
            self.logger.error(f"No events read from chip.")
            raw_data = self.model.read_raw_data(n_events)
            return
        raw_data = self.model.read_raw_data(n_events)
        # ----------------------------------------------------
        # filepath = "./tmp/data_seq.log"
        # if os.path.exists(filepath):
        #     os.remove(filepath)
        # f = open(filepath, "a")
        # for data in raw_data:
        #     f.write(f"{'{0:016b}'.format(data)}\n")
        # f.close()
        # ----------------------------------------------------
        # ---- ASSERT DATA RECEIVED WITH DATA SENT ------
        res = True
        for i, data in enumerate(raw_data):
            if data != fifo_data_in[i]:
                res = False
                self.logger.error("Check FIFO readout FSM test failed.")
                break
        if res:
            self.logger.info(
                "Check FIFO readout FSM checking test completed successfully."
            )
        # ----------- RESET FPGA MODULES ----------
        self.model.device.actions.stop_capture()
        self.model.device.actions.reset_fifo()
        self.model.device.actions.reset_ram()
        self.model.device.actions.reset_aer()

    def light_response(self):
        lightTool = LightResponse()
        lightTool.save(self.model.main_img_data)


class EXT_SIG:
    # RESET CLUSTER CONFIGURATION
    # 2'b00: All clusters enabled
    # 2'b01 - 2'b10 - 2'b11: Only one cluster enabled
    RST_CLUSTER_BIT0 = LINK_VALUE_DEF(16)
    RST_CLUSTER_BIT1 = LINK_VALUE_DEF(17)
    # RESET PIX DEASSERTION CONFIGURATION
    # 1'b0: The rst_pix is deasserted when ACK received from the arbitrer
    # 1'b1: The rst_pix is deasserted when ACK received from the external device
    AER_RST_SRC = LINK_VALUE_DEF(23)
    # AER REQ SOURCE CONFIGURATION
    # 1'b0: The AER REQ comes from pull-down
    # 1'b1: The AER REQ comes from NOR tree
    AER_REQ_SRC = LINK_VALUE_DEF(24)
    # MATRIX CONTROL CONFIGURATION
    # 1'b0: The aer_ack and rst_pix are generated externally
    # 1'b1: The aer_ack and rst_pix comes from the digital block
    SENSOR_CTRL_CFG = LINK_VALUE_DEF(21)
    # PARALELL INTERFACE DATA SOURCE
    # 1'b0: Data from AER bus
    # 1'b1: Data from AER sequencer
    PAR_IFACE_SRC = LINK_VALUE_DEF(22)
    # PARALELL INTERFACE PAD CONFIG
    # 1'b0: Driving configuration from tie cells
    # 1'b1: Driving configuration from register bank
    PAR_IFACE_PAD_CFG = LINK_VALUE_DEF(25)
