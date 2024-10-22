from TAER_App.Initializers.initializer_base import InitializerBase
from TAER_Core.main_model import MainModel
from TAER_Core.Libs import LINK_VALUE_DEF, TRIGGER_DEF
import numpy as np
import time
import cv2 as cv
from io import StringIO


class InitializerSaer(InitializerBase):
    def __init__(self, model: MainModel) -> None:
        super().__init__(model)
        self.chip_name = "chip_mangut"

    def on_start_app(self):
        pass

    def on_close_app(self):
        pass

    def on_init_capture(self):
        self.__set_evt_cnt(self.model)
        pass

    def on_before_capture(self):
        pass

    def on_after_capture(self, raw_data):

        if self.model.current_mode == 4:
            addr = raw_data[0::2]
            data_raw = np.zeros([64, 96])
            """
            for y in range(64):
                for x in range (96):
                    addr_pix = (y << 16) + x
                    data_raw[y,x] = np.sum(addr == addr_pix)
            """

            for i in np.arange(0, len(addr)):
                x = addr[i] & 0xFFFF
                y = (addr[i] >> 16) & 0xFFFF
                if (x < 96) & (y < 64):
                    data_raw[y, x] = data_raw[y, x] + 1

            self.model.main_img_data = data_raw

        elif self.model.current_mode == 0:
            self.model.main_img_data = raw_data
        print("Events: " + str(self.model.device.actions.get_evt_count()))
        self.save_image(raw_data, "data_out.txt")
        pass

    def on_end_capture(self):
        pass

    def __set_evt_cnt(self):
        mode_name = self.model.get_current_mode_name(self.model.current_mode)
        if mode_name == "Raw data" or mode_name == "pDVS":
            self.model.FR_raw_mode_en = True
        else:
            self.model.FR_raw_mode_en = False

    def save_image(self, data_in, path):
        with open(path, "ab") as f:
            np.savetxt(f, data_in)

