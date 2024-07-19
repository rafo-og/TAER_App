import wx
from .pcb_switches_model import PcbSwitchesModel
from .pcb_switches_view import PcbSwitchesView


class PcbSwitchesPresenter:
    def __init__(self, model: PcbSwitchesModel, view: PcbSwitchesView, on_clean=None):
        self.model = model
        self.view = view
        self.interactor = PcbSwitchesInteractor(self, self.view)
        self.on_clean = on_clean

    def start(self):
        self.update_view()
        self.__config_interaction()
        self.view.open()

    def on_close(self):
        self.view.close(True)
        # Dereference all objects to be garbage collected
        self.model = None
        self.view = None
        self.interactor = None
        if self.on_clean is not None:
            self.on_clean()

    def update_view(self):
        values = self.model.pcb_switches
        self.view.update_values(values)

    def __config_interaction(self):
        for widget in self.view.panel_values.values_widgets.values():
            widget.Bind(wx.EVT_CHECKBOX, self.__on_choose_value)

    def __on_choose_value(self, evt):
        evt_widget = evt.GetEventObject()
        model_widgets = self.view.panel_values.values_widgets
        value = None
        for label, widget in model_widgets.items():
            if value is not None:
                break
            if evt_widget.GetId() == widget.GetId():
                for switch in self.model.pcb_switches.values():
                    if value is not None:
                        break
                    if switch.label == label:
                        switch.state = evt_widget.GetValue()
                        self.model.base_model.device.actions.set_pcb_switch(switch.bit, switch.state)


class PcbSwitchesInteractor:
    def __init__(self, presenter, view) -> None:
        self.view = view
        self.presenter = presenter
        self.view.Bind(wx.EVT_CLOSE, self.__on_close)

    def __on_close(self, evt):
        self.presenter.on_close()
