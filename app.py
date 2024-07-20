""" Entry point. """

from TAER_Core.main_presenter import MainPresenter
from TAER_Core.Controllers import MainInteractor
from TAER_Core.main_model import MainModel
from TAER_Core.main_view import MainView

if __name__ == "__main__":
    # Initialize the app
    app = MainPresenter(MainModel(), MainView(), MainInteractor())
    # Start the app
    app.start()
