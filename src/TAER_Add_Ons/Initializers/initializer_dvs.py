from TAER_Core.main_model import MainModel
from TAER_Add_Ons.Initializers.initializer_base import InitializerBase
import numpy as np


class InitializerDVS(InitializerBase):
    def __init__(self, model: MainModel) -> None:
        super().__init__(model)
        self.chip_name = "chip_pablo"

    def on_start_app(self):
        pass

    def on_close_app(self):
        pass

    def on_close_app(self):
        pass

    def on_init_capture(self):
        self.__set_mode_from_name()

    def on_before_capture(self):
        pass

    def on_after_capture(self, raw_data):
        mode_name = self.model.get_current_mode_name(self.model.current_mode)
        if mode_name == "Frame mode":
            frame = np.array(raw_data).astype(np.int32)
            frame_min = -frame.min()
            frame_max = frame.max()
            frame_scaled = frame / np.maximum(frame_min, frame_max) * 127 + 127
            self.model.main_img_data = frame_scaled.astype(np.uint8)
            self.save_image(frame_scaled, "im_pablo_fr.txt")
        else:
            events_addr = raw_data[0:-1:2]
            # events_tstamp = raw_data[1:-2:2]
            frame_event = np.zeros((64, 96))
            for addr in events_addr:
                addr_y = addr >> 16
                addr_x = addr & (2**7 - 1)
                sign = addr & (2**7) >> 7
                if sign:
                    frame_event[addr_y, addr_x] = frame_event[addr_y, addr_x] + 1
                else:
                    frame_event[addr_y, addr_x] = frame_event[addr_y, addr_x] - 1
            frame_event[63, 94] = 0
            events_min = frame_event.min()
            events_max = frame_event.max()
            frame_event = frame_event * 127 / np.maximum(np.abs(events_min), events_max) + 127

            self.model.main_img_data = np.reshape(frame_event.astype(np.uint8), (1, 64 * 96))
            self.save_image(raw_data, "test/saer/im_pablo.txt")
        pass

    def on_end_capture(self):
        pass

    def on_test(self):
        pass

    def __set_mode_from_name(self):
        mode_name = self.model.get_current_mode_name(self.model.current_mode)
        if mode_name == "Event mode":
            self.model.FR_raw_mode_en = True
        else:
            self.model.FR_raw_mode_en = False

    def save_image(self, data_in, path):
        with open(path, "wb") as f:
            np.savetxt(f, data_in)
