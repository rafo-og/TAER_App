import logging
from TAER_Core.main_model import MainModel


class InitializerBase:
    def __init__(self, model: MainModel) -> None:
        self.model = model
        self.chip_name = ""
        self.logger = logging.getLogger("initializer")

    def on_start_app(self):
        pass

    def on_close_app(self):
        pass

    def on_close_app(self):
        pass

    def on_init_capture(self):
        pass

    def on_before_capture(self):
        pass

    def on_after_capture(self, raw_data):
        pass

    def on_end_capture(self):
        pass

    def on_test(self):
        pass
