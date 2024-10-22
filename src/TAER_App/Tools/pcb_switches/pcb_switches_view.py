import wx
import wx.lib.scrolledpanel
from TAER_Core.Views import AuxViewBase


class PcbSwitchesView(AuxViewBase):
    def __init__(self, parent, title) -> None:
        super().__init__(
            parent=parent,
            id=wx.NewId(),
            title=title,
            style=wx.DEFAULT_FRAME_STYLE ^ wx.MAXIMIZE_BOX,
        )
        self.__create_layout()

    def __create_layout(self):
        # Avoid color on background in Windows OS
        self.SetBackgroundColour(wx.NullColour)
        # Sizers
        self.hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.vsizer = wx.BoxSizer(wx.VERTICAL)
        self.hsizer.Add(self.vsizer, 1, wx.EXPAND | wx.ALL, 5)
        # Register bits panel
        self.panel_values = PcbSwitchesPanel(self)
        self.vsizer.Add(self.panel_values, 1, wx.EXPAND | wx.ALL)
        self.SetAutoLayout(True)
        self.SetSizerAndFit(self.hsizer)
        self.Layout()

    def update_values(self, values):
        self.panel_values.update_values(values)
        self.Fit()


class PcbSwitchesPanel(wx.lib.scrolledpanel.ScrolledPanel):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.SetMinClientSize((250, 250))
        self.SetMaxClientSize((400, 600))
        self.SetAutoLayout(True)
        self.SetupScrolling()
        self.__create_layout()
        self.init_flag = False
        self.values_widgets = {}

    def __create_layout(self):
        # Avoid color on background in Windows OS
        self.SetBackgroundColour(wx.NullColour)
        self.hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.hbox.Add(self.vbox, 1, wx.EXPAND | wx.ALL, 1)
        # Set main sizer and fit
        self.SetSizer(self.hbox)
        self.Layout()

    def update_values(self, values):
        if not self.init_flag:
            self.__init_values(values)
            self.init_flag = True
        for value in values.values():
            self.values_widgets[value.label].SetValue(value.state)

    def __init_values(self, values):
        grid_sizer = wx.FlexGridSizer(cols=2, vgap=3, hgap=10)
        for value in values.values():
            grid_sizer.SetFlexibleDirection(wx.HORIZONTAL)
            if hasattr(value, "bit"):
                st1 = wx.StaticText(self, label=value.label, style=wx.CENTER, size=wx.Size(-1, 25))
                grid_sizer.Add(
                    st1,
                    0,
                    wx.ALL | wx.EXPAND | wx.ALIGN_CENTRE_VERTICAL,
                    5,
                )
                t1 = wx.CheckBox(self)
                grid_sizer.Add(t1, 0, wx.ALL | wx.EXPAND | wx.ALIGN_CENTRE_VERTICAL, 5)
                self.values_widgets[value.label] = t1
        self.vbox.Add(grid_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.Layout()
        self.Fit()
