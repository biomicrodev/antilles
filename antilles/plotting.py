import matplotlib.pyplot as plt


class Plotter:
    def __init__(self):
        self.fig: plt.Figure = plt.Figure()

    @staticmethod
    def show() -> None:
        plt.show()
