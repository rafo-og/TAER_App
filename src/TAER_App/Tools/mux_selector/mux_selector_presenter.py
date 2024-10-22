import wx
from .mux_selector_model import MuxSelectorModel
from .mux_selector_view import MuxSelectorView


class MuxSelectorPresenter:
    def __init__(self, model: MuxSelectorModel, view: MuxSelectorView, on_clean=None):
        self.model = model
        self.view = view
        self.interactor = MuxSelectorInteractor(self, self.view)
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
        values = self.model.test_signals
        self.view.update_values(values)

    def __config_interaction(self):
        for widget in self.view.panel_values.values_widgets.values():
            widget.Bind(wx.EVT_COMBOBOX, self.__on_choose_value)

    def __on_choose_value(self, evt):
        evt_widget = evt.GetEventObject()
        model_widgets = self.view.panel_values.values_widgets
        value = None
        for label, widget in model_widgets.items():
            if value is not None:
                break
            if evt_widget.GetId() == widget.GetId():
                for test_signal in self.model.test_signals.values():
                    if value is not None:
                        break
                    for signal in test_signal.reg.signals.values():
                        if signal.label == label:
                            value = [k for k, v in test_signal.values.items() if v == evt_widget.GetValue()]
                            if len(value) != 0:
                                value = value[0]
                                break
                            else:
                                value = None
                self.model.base_model.write_signal(label, value)


class MuxSelectorInteractor:
    def __init__(self, presenter, view) -> None:
        self.view = view
        self.presenter = presenter
        self.view.Bind(wx.EVT_CLOSE, self.__on_close)

    def __on_close(self, evt):
        self.presenter.on_close()
