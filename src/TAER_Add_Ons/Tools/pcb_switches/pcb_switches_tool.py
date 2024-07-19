from .pcb_switches_presenter import PcbSwitchesPresenter
from .pcb_switches_model import PcbSwitchesModel
from .pcb_switches_view import PcbSwitchesView
from ..tool_base import ToolBase


class PcbSwitchesTool(ToolBase):
    def __init__(self, parent_model, parent) -> None:
        super().__init__("PCB Switches")
        self.main_model = parent_model
        self.parent = parent

    def open(self):
        if self.is_enabled:
            self.presenter = PcbSwitchesPresenter(
                PcbSwitchesModel(self.main_model, self.config),
                PcbSwitchesView(self.parent, self.name),
                self.close,
            )
            self.presenter.start()

    def close(self):
        self.presenter = None

    def update_view(self):
        self.presenter.update_view()

    def is_shown(self):
        if hasattr(self, "presenter") and self.presenter is not None:
            return self.presenter.view.IsShown()
        else:
            return False
