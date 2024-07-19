import wx
import wx.lib.scrolledpanel
from TAER_Core.Views import AuxViewBase


class MuxSelectorView(AuxViewBase):
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
        self.panel_values = MuxSelectorPanel(self)
        self.vsizer.Add(self.panel_values, 1, wx.EXPAND | wx.ALL)
        self.SetAutoLayout(True)
        self.SetSizerAndFit(self.hsizer)
        self.Layout()

    def update_values(self, values):
        self.panel_values.update_values(values)
        self.Fit()


class MuxSelectorPanel(wx.lib.scrolledpanel.ScrolledPanel):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.SetMinClientSize((450, 600))
        self.SetMaxClientSize((600, 1000))
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

    def update_values(self, ivalues):
        if not self.init_flag:
            self.__init_values(ivalues)
            self.init_flag = True
        for _, ivalue in ivalues.items():
            for _, signal in ivalue.reg.signals.items():
                if signal.label == ivalue.label:
                    res = ivalue.reg.get_signal(signal.label)
                    choice_value = ivalue.values[res]
                    self.values_widgets[signal.label].SetValue(choice_value)
                    break

    def __init_values(self, values):
        old_label = None
        for value in values.values():
            if (old_label is None) or (value.reg.label != old_label):
                sizer = wx.StaticBoxSizer(wx.HORIZONTAL, self, value.reg.label)
                self.vbox.Add(sizer, 0, wx.EXPAND | wx.ALL, 5)
                grid_sizer = wx.FlexGridSizer(cols=2, vgap=3, hgap=10)
                grid_sizer.SetFlexibleDirection(wx.HORIZONTAL)
                sizer.Add(grid_sizer, 1, wx.ALL | wx.EXPAND, 5)
            old_label = value.reg.label
            st1 = wx.StaticText(self, label=value.caption, style=wx.CENTER, size=wx.Size(-1, 25))
            grid_sizer.Add(
                st1,
                0,
                wx.ALL | wx.EXPAND | wx.ALIGN_CENTRE_VERTICAL,
                5,
            )
            choices_names = list(value.values.values())
            t1 = wx.ComboBox(
                self,
                id=wx.NewId(),
                choices=choices_names,
                style=wx.CB_SIMPLE | wx.CB_DROPDOWN | wx.CB_READONLY | wx.CB_SORT,
                size=wx.Size(-1, 25),
            )
            grid_sizer.Add(t1, 0, wx.ALL | wx.EXPAND | wx.ALIGN_CENTRE_VERTICAL, 5)
            self.values_widgets[value.label] = t1
        self.Layout()
        self.Fit()
