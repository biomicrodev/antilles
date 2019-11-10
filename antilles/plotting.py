import matplotlib.pyplot


class Plotter:
    def __init__(self):
        self.fig = matplotlib.pyplot.Figure()

    @staticmethod
    def show() -> None:
        matplotlib.pyplot.show()