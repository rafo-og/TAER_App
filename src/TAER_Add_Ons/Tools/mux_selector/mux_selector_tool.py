from .mux_selector_presenter import MuxSelectorPresenter
from .mux_selector_model import MuxSelectorModel
from .mux_selector_view import MuxSelectorView
from ..tool_base import ToolBase


class MuxSelectorTool(ToolBase):
    def __init__(self, parent_model, parent) -> None:
        super().__init__("Mux Selector")
        self.main_model = parent_model
        self.parent = parent

    def open(self):
        if self.is_enabled:
            self.presenter = MuxSelectorPresenter(
                MuxSelectorModel(self.main_model, self.config),
                MuxSelectorView(self.parent, self.name),
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
