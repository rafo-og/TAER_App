import os
import threading
import time
import logging
from datetime import date
import pickle
import wx
from wx.lib.pubsub import pub as Publisher
import numpy as np
from TAER_Core.Views.auxiliar_view_base import AuxViewBase

# datetime_str = date.today().strftime("%d_%m_%Y")
datetime_str = "31_01_2024"
onedrive_path = os.getenv("OneDrive")

# Power sweep (490, 140) -
# FRAME_POSITION = wx.Point(490, 140)
# DATASET_FOLDER = os.path.join(onedrive_path, "TIC-179\\SCP\\TEST\\data\\SC_CAL")
# OUTPUT_FOLDER = os.path.join(onedrive_path, f"TIC-179\\SCP\\TMP\\SC_CAL\\data_{datetime_str}")
# NSAMPLES = 1000

# Power sweep (730, 59) - 11/01/2024
FRAME_POSITION = wx.Point(730, 59)
DATASET_FOLDER = os.path.join(onedrive_path, "TIC-179\\SCP\\TMP\\SC_INPUTS_TMP")
# DATASET_FOLDER = os.path.join(onedrive_path, "TIC-179\\SCP\\TEST\\outputs\\SC_CAL")
OUTPUT_FOLDER = os.path.join(onedrive_path, f"TIC-179\\SCP\\TMP\\SC_CAL\\data_{datetime_str}")
NSAMPLES = 500
ONE_SAMPLE_MODE = False

# RGB set generation -> Windows position: (742,19)
# FRAME_POSITION = wx.Point(742,19)
# DATASET_FOLDER = os.path.join(onedrive_path, "TIC-179\\SCP\\TMP\\RGB")
# OUTPUT_FOLDER = os.path.join(onedrive_path, f"TIC-179\\SCP\\TMP\\RGB_RES_{datetime_str}")
# NSAMPLES = 1

# RGB SC set generation -> Windows position: (665,19)
# FRAME_POSITION = wx.Point(665,19)
# DATASET_FOLDER = os.path.join(onedrive_path, "TIC-179\\SCP\\TMP\\SC_RGB")
# OUTPUT_FOLDER = os.path.join(
#     onedrive_path, f"TIC-179\\SCP\\TMP\\SC_RGB_RES_{datetime_str}"
# )
# NSAMPLES = 1

TIME_STEP_SEC = 0
IMAGE_SIZE = 600
MIN_EVENTS = 1
# MIN_EVENTS = 30000
INT_PERIOD_STEP = 500000000
MAX_ATTEMPS = 2
FR_RAW_PRESET_PATH = os.path.join(onedrive_path, "TIC-179/SCP/PRESETS/fr_ibias_raw.preset")
FR_PRESET_PATH = os.path.join(onedrive_path, "TIC-179/SCP/PRESETS/fr_ibias_getset_test.preset")
SCP_PRESET_PATH = os.path.join(onedrive_path, "TIC-179/SCP/PRESETS/scp_ibias_getset_test.preset")

# Presenter


class DataSetGatheringPresenter:
    def __init__(self, model) -> None:
        self.model = model
        # Logging
        self.logger = logging.getLogger("test")
        self.view = DataSetGatheringView(None)
        self.delegates = DataSetGatheringDelegates(self, self.view)
        self.view.set_paths(DATASET_FOLDER, OUTPUT_FOLDER)
        self.isGathering = False
        self.stopFlag = False
        self.prev_raw_state = None
        # create a pubsub receiver
        Publisher.subscribe(self.unlock_image_update_wait, "test_img_update")
        self.img_lock = None

    def start(self):
        self.stopFlag = False
        self.view.open()

    def stop(self):
        self.stopFlag = True
        self.gather_thread.join()
        self.stopFlag = False
        self.isGathering = False
        self.stopFlag = False
        self.prev_raw_state = None
        self.view.label_panel.start_test_btn.SetLabelText("Start")

    def on_start_gathering(self):
        if not self.isGathering:
            wx.CallAfter(self.view.set_sample, 1)
            self.gather_thread = threading.Thread(target=self.gathering)
            self.timer_thread = threading.Thread(target=self.process_timer)
            self.isGathering = True
            self.gather_thread.start()
            self.timer_thread.start()
        else:
            self.stop()
            self.isGathering = False

    def gathering(self):
        self.look_over_folder_tree(DATASET_FOLDER)
        wx.CallAfter(self.view.label_panel.start_test_btn.SetLabelText, "Start")
        self.model.TFS_raw_mode_en = self.prev_raw_state
        self.isGathering = False

    def look_over_folder_tree(self, path):
        self.prev_raw_state = self.model.TFS_raw_mode_en
        for file in reversed(os.listdir(path)):
            if self.stopFlag:
                break
            d = os.path.join(path, file)
            if os.path.isfile(d):
                if d.lower().endswith((".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif")):
                    self.get_image(d)
            elif os.path.isdir(d):
                self.look_over_folder_tree(d)

    def process_timer(self):
        start_time = time.time()
        while self.isGathering:
            elapsed_time = time.time() - start_time
            delta_time = time.gmtime(elapsed_time)
            time_string = f"{str(delta_time.tm_mday-1).zfill(2)}:{str(delta_time.tm_hour).zfill(2)}:{str(delta_time.tm_min).zfill(2)}:{str(delta_time.tm_sec).zfill(2)}"
            wx.CallAfter(self.view.set_time, time_string)
            time.sleep(1)

    def get_image(self, path):
        self.power_sweep(path)
        # self.snr_cte_check(path)

    def get_capture(self):
        raw_data = None
        nevents_read = None
        self.model.device.actions.events_done()
        self.model.device.actions.start_capture()
        if self.model.TFS_raw_mode_en:
            read_flag = self.wait_until(self.model.device.actions.is_captured, 120)
            if not read_flag:
                self.logger.error("Image readout timeout.")
            else:
                self.model.device.actions.stop_capture()
                nevents_read = self.model.device.actions.get_evt_count()
                ndata_to_read = (nevents_read // 4) * 32
                raw_data = self.model.read_raw_data(ndata_to_read)
        elif self.model.FR_raw_mode_en:
            nevents_read = (self.model.read_dev_register("N_EVENTS") // 4) * 32
            read_flag = self.wait_until(self.model.device.actions.events_done, 60)
            self.model.device.actions.stop_capture()
            if not read_flag:
                self.logger.error("Image readout timeout.")
            else:
                raw_data = self.model.read_raw_data(nevents_read)
        else:
            read_flag = self.wait_until(self.model.device.actions.is_captured, 120)
            if not read_flag:
                self.logger.error("Image readout timeout.")
            else:
                raw_data = self.model.read_image()
        self.model.device.actions.stop_capture()
        self.model.device.actions.reset_fifo()
        self.model.device.actions.reset_ram()
        self.model.device.actions.reset_aer()
        return raw_data, nevents_read

    def save_image(self, img_path, data, sample=None):
        path_to_save = img_path.replace(DATASET_FOLDER, OUTPUT_FOLDER)
        pre, ext = os.path.splitext(path_to_save)
        if sample is not None:
            if ONE_SAMPLE_MODE or NSAMPLES > 1:
                filename = os.path.basename(pre)
                os.makedirs(os.path.dirname(pre), exist_ok=True)
                path_to_save = os.path.join(pre, filename + "_" + str(sample) + ".bin")
            else:
                path_to_save = pre + ".bin"
        else:
            path_to_save = pre + ".bin"
        self.logger.info(path_to_save)
        os.makedirs(os.path.dirname(path_to_save), exist_ok=True)
        with open(path_to_save, "w") as f:
            data.tofile(f)  # To recover the info use fromfile function

    def wait_until(self, somepredicate, timeout, period=0.25, *args, **kwargs):
        mustend = time.time() + timeout
        while time.time() < mustend:
            if somepredicate(*args, **kwargs):
                return True
            time.sleep(period)
        return False

    def load_preset(self, preset):
        with open(preset, "rb") as fp:
            to_load = pickle.load(fp)
        if to_load is not None:
            self.model.set_preset(to_load)

    def save_preset(self, path):
        to_save = self.model.get_preset()
        with open(path, "wb") as fp:
            pickle.dump(to_save, fp, pickle.HIGHEST_PROTOCOL)

    def apply_delta_integration_time(self, delta_time: np.uint32):
        curr_int_period = self.model.read_dev_register("T_PERIOD")
        self.model.write_dev_register("T_PERIOD", curr_int_period + delta_time)
        curr_int_period = self.model.read_dev_register("T_PIXON")
        self.model.write_dev_register("T_PIXON", curr_int_period + delta_time)
        self.logger.info(f"Integration time updated to ({curr_int_period + delta_time})")

    # Specific experiments methods
    def unlock_image_update_wait(self):
        if self.img_lock is not None:
            self.img_lock.release()

    def power_sweep(self, path):
        attemp = 0
        self.img_lock = threading.Semaphore(0)
        try:
            wx.CallAfter(self.view.set_image, path)
            self.img_lock.acquire()
            # GET FREE RUNNING IMAGE (FOR GROUND TRUTH COMPARISON)
            self.load_preset(FR_PRESET_PATH)
            self.model.TFS_raw_mode_en = False
            raw_data, _ = self.get_capture()
            self.save_image(path, raw_data, "FR")
            # GET NSAMPLES TIMES THE SAME SPATIAL CONTRAST IMAGE (TEMPORAL NOISE REDUCTION)
            self.load_preset(SCP_PRESET_PATH)
            self.model.TFS_raw_mode_en = True
            if not ONE_SAMPLE_MODE:
                for i in range(1, NSAMPLES + 1):
                    if self.stopFlag:
                        break
                    wx.CallAfter(self.view.set_sample, i)
                    raw_data, events_read = self.get_capture()
                    while events_read < MIN_EVENTS:
                        if attemp == MAX_ATTEMPS:
                            break
                        self.logger.info(f"Events capture less than minimum ({events_read})")
                        self.apply_delta_integration_time(INT_PERIOD_STEP)
                        raw_data, events_read = self.get_capture()
                        attemp = attemp + 1
                    if raw_data is not None:
                        self.save_image(path, raw_data, i)
        except Exception as e:
            self.logger.error(e)
        if TIME_STEP_SEC > 0:
            time.sleep(TIME_STEP_SEC)

    def snr_cte_check(self, path):
        try:
            wx.CallAfter(self.view.set_image, path)
            time.sleep(5)
            # GET FREE RUNNING IMAGE (FOR GROUND TRUTH COMPARISON)
            self.load_preset(FR_RAW_PRESET_PATH)
            self.model.FR_raw_mode_en = True
            self.model.TFS_raw_mode_en = False
            if not ONE_SAMPLE_MODE:
                for i in range(1, NSAMPLES + 1):
                    if self.stopFlag:
                        break
                    wx.CallAfter(self.view.set_sample, i)
                    raw_data, _ = self.get_capture()
                    self.save_image(path, raw_data, f"FRRAW_{i}")
        except Exception as e:
            self.logger.error(e)
        if TIME_STEP_SEC > 0:
            time.sleep(TIME_STEP_SEC)


# View


class DataSetGatheringView(AuxViewBase):
    def __init__(self, parent):
        super().__init__(
            parent=parent,
            id=wx.NewId(),
            title="Get dataset",
            style=wx.DEFAULT_FRAME_STYLE ^ wx.MAXIMIZE_BOX ^ wx.RESIZE_BORDER,
        )
        self.__create_layout()
        self.SetPosition(FRAME_POSITION)

    def __create_layout(self):
        # Avoid color on background in Windows OS
        self.SetBackgroundColour(wx.NullColour)

        self.image_panel = DataSetGatheringImagePanel(self)
        self.label_panel = DataSetGatheringLabelsPanel(self)
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.hbox = wx.BoxSizer(wx.HORIZONTAL)

        self.vbox.Add(self.image_panel, 1, wx.EXPAND | wx.ALL, 5)
        self.vbox.Add(self.label_panel, 0, wx.EXPAND | wx.ALL, 5)
        self.hbox.Add(self.vbox, 1, wx.EXPAND | wx.ALL, 1)
        self.Layout()
        self.SetSizerAndFit(self.hbox)

    def set_image(self, img_path):
        path = img_path.replace(DATASET_FOLDER, "")
        self.label_panel.image_name.SetLabel("Image path: " + path)
        self.image_panel.set_image(img_path)
        self.Layout()
        self.Fit()
        wx.CallAfter(Publisher.sendMessage, "test_img_update")

    def set_paths(self, dataset_path, output_path):
        path = "DATASET PATH: " + dataset_path
        self.label_panel.dataset_path_txt_box.SetLabel(path)
        path = "OUTPUT PATH: " + output_path
        self.label_panel.output_path_txt_box.SetLabel(path)
        self.label_panel.Layout()
        self.Layout()

    def set_sample(self, sample):
        self.label_panel.image_sample.SetLabel(f"Sample: {sample}/{NSAMPLES}")
        self.label_panel.Layout()

    def set_time(self, time):
        self.label_panel.process_time.SetLabel(f"Time elapsed: {time}")
        self.label_panel.Layout()


class DataSetGatheringImagePanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        self.PhotoMaxSize = IMAGE_SIZE
        self.__create_layout()

    def __create_layout(self):
        # Avoid color on background in Windows OS
        self.SetBackgroundColour(wx.NullColour)
        self.hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        img = wx.Image(IMAGE_SIZE, IMAGE_SIZE)
        self.imageCtrl = wx.StaticBitmap(self, wx.ID_ANY, wx.Bitmap(img))
        self.vbox.Add(self.imageCtrl, 1, wx.EXPAND | wx.ALL, 1)
        self.hbox.Add(self.vbox, 1, wx.EXPAND | wx.ALL, 1)
        self.SetSizer(self.hbox)
        self.Layout()

    def set_image(self, path):
        img = wx.Image(path, wx.BITMAP_TYPE_ANY)
        # scale the image, preserving the aspect ratio
        W = img.GetWidth()
        H = img.GetHeight()
        if W > H:
            NewW = self.PhotoMaxSize
            NewH = self.PhotoMaxSize * H / W
        else:
            NewH = self.PhotoMaxSize
            NewW = self.PhotoMaxSize * W / H
        img = img.Scale(int(NewW), int(NewH))
        self.imageCtrl.SetBitmap(wx.Bitmap(img))
        self.Refresh()


class DataSetGatheringLabelsPanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        self.__create_layout()

    def __create_layout(self):
        # Avoid color on background in Windows OS
        self.SetBackgroundColour(wx.NullColour)
        # Create controls
        self.position_txt_box = wx.StaticText(self, label="(X, Y): ", style=wx.ALIGN_CENTRE)
        self.image_name = wx.StaticText(self, label="Image path: ", style=wx.ALIGN_CENTRE)
        self.image_sample = wx.StaticText(self, label=f"Sample: 0/{NSAMPLES}", style=wx.ALIGN_CENTRE)
        self.process_time = wx.StaticText(
            self,
            label=f"Time elapsed: 00:00:00:00",
            style=wx.ALIGN_CENTRE,
        )
        self.start_test_btn = wx.Button(self, label="Start")
        self.dataset_path_txt_box = wx.StaticText(self, label="", style=wx.ALIGN_CENTRE)
        self.output_path_txt_box = wx.StaticText(self, label="", style=wx.ALIGN_CENTRE)
        # Create boxes
        self.hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        # Place controls
        self.vbox.Add(self.position_txt_box, 0, wx.EXPAND | wx.CENTER | wx.BOTTOM | wx.TOP, 5)
        self.vbox.Add(self.image_name, 0, wx.EXPAND | wx.CENTER, 0)
        self.vbox.Add(self.image_sample, 0, wx.EXPAND | wx.CENTER, 0)
        self.vbox.Add(self.process_time, 0, wx.EXPAND | wx.CENTER, 0)
        self.vbox.Add(self.start_test_btn, 0, wx.CENTER | wx.BOTTOM | wx.TOP, 2)
        self.vbox.Add(self.dataset_path_txt_box, 0, wx.EXPAND | wx.CENTER | wx.TOP, 3)
        self.vbox.Add(self.output_path_txt_box, 0, wx.EXPAND | wx.CENTER | wx.BOTTOM, 10)
        self.hbox.Add(self.vbox, 1, wx.EXPAND | wx.ALL, 1)
        self.Layout()
        self.SetSizerAndFit(self.hbox)


# Interactor and delegates


class DataSetGatheringDelegates:
    def __init__(self, presenter, view) -> None:
        self.view = view
        self.presenter = presenter
        self.view.label_panel.start_test_btn.Bind(wx.EVT_BUTTON, self.onStart)
        self.view.Bind(wx.EVT_MOVE, self.OnMove)

    def onStart(self, event):
        if self.view.label_panel.start_test_btn.GetLabel() == "Start":
            self.view.label_panel.start_test_btn.SetLabelText("Stop")
        else:
            self.view.label_panel.start_test_btn.SetLabelText("Start")
        self.view.Refresh()

        self.presenter.on_start_gathering()

    def OnMove(self, event):
        x, y = self.view.GetPosition()
        self.view.label_panel.position_txt_box.SetLabel(f"(X, Y): ({x}, {y})")
        self.view.label_panel.Layout()
