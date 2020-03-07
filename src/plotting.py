from typing import List, Dict, Tuple
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.dates as mdates
from matplotlib.ticker import (MultipleLocator, FormatStrFormatter,
                               AutoMinorLocator)
import src.utils as utils


month = mdates.MonthLocator()
days = mdates.DayLocator()


class LengthError(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


def plot_csv(dark=True):
    x_c, y_c = make_courbe(utils._CONFIRMED_PATH)
    x_r, y_r = make_courbe(utils._RECOVERED_PATH)
    x_d, y_d = make_courbe(utils._DEATH_PATH)
    fig, ax = plt.subplots()
    ax.spines['bottom'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)

    ax.xaxis.set_major_locator(MultipleLocator(7))

    ax.plot(x_c, y_c, "w.-")
    ax.plot(x_r, y_r, "g.-")
    ax.plot(x_d, y_d, "r.-")

    ticks = [i for i in range(len(y_c)) if i % 7 == 0]
    plt.xticks(ticks)
    plt.grid(True)
    plt.ylabel("Total confirmed cases")
    plt.xlabel("Timeline (MM/DD/YYYY)")

    if dark:
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
        leg = plt.legend(["Total confirmed", "Total recovered", "Total deaths"], facecolor='0.1')
        for text in leg.get_texts():
            text.set_color("white")
        plt.savefig("stats.png", transparent=True)
    else:
        leg = plt.legend(["Total confirmed", "Total recovered", "Total deaths"])
        plt.savefig("stats.png")
    plt.close(fig)

def make_courbe(fpath: str) -> Tuple[List, List]:
    datas = utils.data_reader(fpath)
    d = {}
    x = []
    y = []
    for data in datas:
        i = 0
        for k, v in data.items():
            if i > 3: # we are only interested by numbers
                if k not in d:
                    d[k] = int(v)
                else:
                    d[k] += int(v)
            i += 1
    for parse_k, parse_v in d.items():
        x.append(parse_k)
        y.append(parse_v)
    if len(x) == len(y):
        return x, y
    raise LengthError(f"x, y have a different length, x = {len(x)}, y = {len(y)}")


if __name__ == "__main__":
    plot_csv()
