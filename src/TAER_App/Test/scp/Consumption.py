import os
import threading
import time
import pickle
import logging
from datetime import date
import numpy as np
import wx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wxagg import (
    NavigationToolbar2WxAgg as NavigationToolbar2Wx,
)
from unit_parse import parser
from TAER_App.Test.libs.KEYSIGHT_34465A import KEYSIGHT_34465A
from TAER_Core.Views.auxiliar_view_base import AuxViewBase

datetime_str = date.today().strftime("%d_%m_%Y")
# root_path = os.getenv("OneDrive")
# MEAS_FOLDER = os.path.join(root_path, f"TIC-179/SCP/TMP/experiments/{datetime_str}/consumption")
# SAMPLE_FOLDER = os.path.join(root_path, f"TIC-179/SCP/TMP/experiments/{datetime_str}/consumption/samples")
root_path = os.getenv("HOME")
if root_path is None:
    root_path = os.getcwd()
MEAS_FOLDER = os.path.join(
    root_path, f"Documents/EXPERIMENTS/{datetime_str}/consumption"
)
SAMPLE_FOLDER = os.path.join(
    root_path, f"Documents/EXPERIMENTS/{datetime_str}/consumption/samples"
)
MEAS_FILENAME = "meas.log"
SAMPLE_FILENAME = "sample.log"
NSAMPLES = 1000


# Presenter
class ConsumptionTest:
    def __init__(self, model) -> None:
        self.model = model
        # Logging
        self.logger = logging.getLogger("test")
        self.view = ConsumptionTestView()
        self.delegates = ConsumptionTestDelegates(self, self.view)
        self.dev = KEYSIGHT_34465A()
        self.HEADER = "Key,Measure,Sigma,Events,File\n"
        self.img_lock = None
        self.filename = self.create_meas_file(MEAS_FOLDER, MEAS_FILENAME)
        self.curr_meas = None
        self.tag = None

    def start(self):
        self.stopFlag = False
        self.view.open()

    def reset(self):
        self.dev.reset()
        self.filename = self.create_meas_file(MEAS_FOLDER, MEAS_FILENAME)

    def save_samples(self, data, tag):
        filename = self.__save_raw_data(tag, data)
        self.__save_meas_point(tag, data, filename)
        self.logger.info("Data saved.")

    def __create_new_filename(self, path):
        filename, extension = os.path.splitext(path)
        counter = 1
        while os.path.exists(path):
            path = filename + "_" + str(counter) + extension
            counter += 1
        return path

    def __check_csv_header(self):
        filename = os.path.join(MEAS_FOLDER, self.filename)
        header = ""
        f = open(filename)
        f.seek(0, 0)
        header = f.readline()
        f.close()
        if header != self.HEADER:
            with open(filename, "a") as f:
                f.seek(0, 0)
                f.write(self.HEADER)

    def __save_meas_point(self, tag, data, raw_data_filename):
        self.__check_csv_header()
        filename = os.path.join(MEAS_FOLDER, self.filename)
        key = tag
        meas_mean = "{:.4e}".format(np.mean(data))
        meas_sigma = "{:.4e}".format(np.std(data))
        evnt = self.model.device.actions.get_evt_count()
        file = raw_data_filename.replace("/", "\\")
        with open(filename, "a") as f:
            f.write(f"{key}, {meas_mean}, {meas_sigma}, {evnt}, {file}\n")

    def __save_raw_data(self, tag, data):
        filepath = os.path.join(SAMPLE_FOLDER, f"sample_{tag}.log")
        filename = self.__create_new_filename(filepath)
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        data = np.asarray(data)
        with open(filename, "w") as f:
            data.tofile(f)  # To recover the info use fromfile function
        return filename

    def trig_measure(self):
        self.thread = threading.Thread(target=self.measure)
        self.thread.start()

    def measure(self):
        try:
            self.dev.clear()
            self.dev.cfg_dc_amp()
            self.dev.cfg_dc_amp_range(self.__get_range())
            self.dev.trig_dc_amp_meas(NSAMPLES, 1)
            self.curr_meas = self.dev.read_dc_amp_meas()
            self.tag = self.view.tag_btxt.GetLineText(0)
            wx.CallAfter(self.view.plot_samples, self.curr_meas)
        except Exception as e:
            print(e)

    def create_meas_file(self, path, name):
        filepath = os.path.join(path, name)
        filename = self.__create_new_filename(filepath)
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            f.write(self.HEADER)
        return filename

    def __get_range(self):
        range_idx = self.view.range_combobox.GetCurrentSelection()
        range_str = self.view.range_combobox.GetString(range_idx)
        range = parser(range_str)
        return range.to("ampere").magnitude


# View


class ConsumptionTestView(AuxViewBase):
    def __init__(self):
        pWindow = wx.GetTopLevelWindows()[0]
        parent = wx.GetTopLevelParent(pWindow)
        super().__init__(
            parent=parent,
            title="Measuring tool",
            style=wx.DEFAULT_FRAME_STYLE ^ wx.MAXIMIZE_BOX ^ wx.RESIZE_BORDER,
        )
        self.__create_layout()

    def __create_layout(self):
        # Avoid color on background in Windows OS
        self.SetBackgroundColour(wx.NullColour)

        self.plot_panel = wx.Panel(self, name="Plot panel")
        self.ctrl_panel = wx.Panel(self, name="Control panel")
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.hbox = wx.BoxSizer(wx.HORIZONTAL)

        self.__plot_panel_layout()
        self.__ctrl_panel_layout()

        self.vbox.Add(self.plot_panel, 1, wx.EXPAND | wx.ALL, 5)
        self.vbox.Add(self.ctrl_panel, 0, wx.EXPAND | wx.ALL, 5)
        self.hbox.Add(self.vbox, 1, wx.EXPAND | wx.ALL, 1)
        self.Layout()
        self.SetSizerAndFit(self.hbox)

    def __plot_panel_layout(self):
        plt.rcParams.update({"font.size": 8})
        self.fig, self.ax = plt.subplots(1, 1, figsize=(2, 1))
        plt.close(self.fig)
        self.canvas = FigureCanvas(self.plot_panel, -1, self.fig)
        self.toolbar = NavigationToolbar2Wx(self.canvas)
        self.toolbar.Realize()

        self.plot_vbox = wx.BoxSizer(wx.VERTICAL)
        self.plot_hbox = wx.BoxSizer(wx.HORIZONTAL)

        self.plot_vbox.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)
        self.plot_vbox.Add(self.toolbar, 0, wx.LEFT | wx.EXPAND)
        self.plot_hbox.Add(self.plot_vbox, 1, wx.EXPAND | wx.ALL, 1)
        self.plot_panel.Layout()
        self.plot_panel.SetSizerAndFit(self.plot_hbox)

    def __ctrl_panel_layout(self):
        self.ctrl_vbox = wx.BoxSizer(wx.VERTICAL)
        self.ctrl_hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        self.ctrl_hbox2 = wx.BoxSizer(wx.HORIZONTAL)

        self.tag_txt = wx.StaticText(
            self.ctrl_panel, label=f"Meas. tag", style=wx.ALIGN_RIGHT
        )
        self.tag_btxt = wx.TextCtrl(self.ctrl_panel, name="Tag text box")
        self.get_measure_btn = wx.Button(self.ctrl_panel, label="Trig. meas.")
        self.rst_btn = wx.Button(self.ctrl_panel, label="Reset instr.")
        self.save_btn = wx.Button(self.ctrl_panel, label="Save")
        self.mean_txt = wx.StaticText(
            self.ctrl_panel, label=f"Mean: 0.00E+00", style=wx.ALIGN_CENTRE
        )
        self.sigma_txt = wx.StaticText(
            self.ctrl_panel, label=f"Sigma: 0.00E+00", style=wx.ALIGN_CENTRE
        )
        self.__create_range_combobox()

        self.ctrl_hbox1.Add(self.save_btn, 0, wx.CENTER | wx.BOTTOM | wx.TOP, 2)
        self.ctrl_hbox1.Add(self.tag_txt, 0, wx.CENTER | wx.LEFT | wx.RIGHT, 10)
        self.ctrl_hbox1.Add(self.tag_btxt, 0, wx.CENTER | wx.LEFT | wx.RIGHT, 10)
        self.ctrl_hbox1.Add(self.range_combobox, 0, wx.CENTER | wx.LEFT | wx.RIGHT, 10)
        self.ctrl_hbox2.Add(self.get_measure_btn, 0, wx.CENTER | wx.BOTTOM | wx.TOP, 2)
        self.ctrl_hbox2.Add(self.rst_btn, 0, wx.CENTER | wx.BOTTOM | wx.TOP, 2)
        self.ctrl_hbox2.Add(self.mean_txt, 0, wx.CENTER | wx.LEFT | wx.RIGHT, 10)
        self.ctrl_hbox2.Add(self.sigma_txt, 0, wx.CENTER | wx.LEFT | wx.RIGHT, 10)
        self.ctrl_vbox.Add(self.ctrl_hbox1, 1, wx.EXPAND | wx.ALL, 1)
        self.ctrl_vbox.Add(self.ctrl_hbox2, 1, wx.EXPAND | wx.ALL, 1)
        self.ctrl_panel.Layout()
        self.ctrl_panel.SetSizerAndFit(self.ctrl_vbox)

    def __create_range_combobox(self):
        cstyle = wx.CB_DROPDOWN | wx.CB_READONLY
        cchoices = ["1uA", "10uA", "100uA", "1mA", "10mA", "100mA", "1A"]
        self.range_combobox = wx.ComboBox(
            self.ctrl_panel, choices=cchoices, style=cstyle, value="1A"
        )

    def plot_samples(self, data):
        t = np.arange(1, len(data) + 1)
        self.ax.cla()
        self.ax.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
        self.ax.plot(t, data)
        self.canvas.draw()
        self.plot_panel.Update()
        self.Update()
        self.plot_panel.Layout()
        self.Layout()
        num = "{:.2e}".format(np.mean(data))
        self.mean_txt.SetLabel(f"Mean: {num}")
        num = "{:.2e}".format(np.std(data))
        self.sigma_txt.SetLabel(f"Sigma: {num}")


# Interactor and delegates


class ConsumptionTestDelegates:
    def __init__(self, presenter: ConsumptionTest, view: ConsumptionTestView) -> None:
        self.view = view
        self.presenter = presenter
        self.view.Bind(wx.EVT_CLOSE, self.onClose)
        self.view.get_measure_btn.Bind(wx.EVT_BUTTON, self.onGetMeasure)
        self.view.rst_btn.Bind(wx.EVT_BUTTON, self.onReset)
        self.view.save_btn.Bind(wx.EVT_BUTTON, self.onSave)

    def onGetMeasure(self, event):
        self.presenter.trig_measure()

    def onSave(self, event):
        self.presenter.save_samples(self.presenter.curr_meas, self.presenter.tag)

    def onReset(self, event):
        self.presenter.reset()

    def onClose(self, event):
        self.view.close(True)


if __name__ == "__main__":
    wxApp = wx.App()
    app = ConsumptionTest(None)
    app.start()
    wxApp.MainLoop()
