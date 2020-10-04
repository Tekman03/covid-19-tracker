import datetime
from typing import Dict, List, Tuple

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage.filters import gaussian_filter1d
from aiohttp import ClientSession
from matplotlib.ticker import (AutoMinorLocator, FormatStrFormatter,
                               MultipleLocator)

import src.utils as utils

month = mdates.MonthLocator()
days = mdates.DayLocator()


class LengthError(Exception):
    pass


class PlotEmpty(Exception):
    pass


def rearrange(timeline, confirmed, recovered, deaths, active):
    i = 0
    while confirmed[i] == 0:
        i += 1
    return timeline[i:], confirmed[i:], logarify(recovered[i:]), logarify(deaths[i:]), logarify(active[i:])

def fix_peaks(peaks):
    """
    This function is meant to remove or at least reduce
    the data peaks when issues are occuring on the API
    """
    for i in range(1, len(peaks)):
        if (peaks[i] - peaks[i-1]) < 0:
            peaks[i] = peaks[i-1]
    return peaks

def fix_active_peaks(peaks):
    """
    This function is meant to remove or at least reduce
    the data peaks when issues are occuring on the API
    """
    for i in range(1, len(peaks) - 1):
        if (peaks[i-1] < peaks[i] and peaks[i+1] < peaks[i]) \
        or (peaks[i-1] > peaks[i] and peaks[i+1] > peaks[i]):
            peaks[i] = peaks[i-1]
    return peaks

def logarify(y):
    for i in range(len(y)):
        if y[i] == 0:
            y[i] = 1
    return y

async def plot_csv(path,
    total_confirmed,
    total_recovered,
    total_deaths,
    logarithmic=False,
    is_us=False,
    is_daily=False):
    timeline, confirmed, recovered, deaths, active = await make_courbe(
        total_confirmed,
        total_recovered,
        total_deaths, is_us=is_us)
    alpha = .2
    fig, ax = plt.subplots()
    ax.spines['bottom'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)

    if logarithmic:
        plt.yscale('log')

    ax.xaxis.set_major_locator(MultipleLocator(7))
    ax.plot(timeline, fix_peaks(deaths), "-", color="#e62712")
    ax.plot(timeline, fix_peaks(confirmed), "-", color="orange")
    if not is_us:
        ax.plot(timeline, fix_active_peaks(active), "-", color="yellow", alpha=0.5)
        ax.plot(timeline, fix_peaks(recovered), "-", color="lightgreen")
        leg = plt.legend(["Deaths", "Confirmed", "Active", "Recovered"], facecolor='0.1', loc="upper left")
    else:
        leg = plt.legend(["Deaths", "Confirmed"], facecolor='0.1', loc="upper left")

    for text in leg.get_texts():
        text.set_color("white")
    ticks = [i for i in range(len(timeline)) if i % 30 == 0]
    plt.xticks(ticks, ha="center")
    ax.yaxis.grid(True)
    plt.ylabel("Data")
    plt.xlabel("Timeline (mm/dd)")

    ax.xaxis.label.set_color('white')
    ax.yaxis.label.set_color('white')
    ax.tick_params(axis='x', colors='white')
    ax.tick_params(axis='y', colors='white')



    if not logarithmic:
        ax.set_ylim(ymin=1)
    ylabs = []
    locs, _ = plt.yticks()

    if logarithmic:
        locs = list(map(lambda x: x * 100, locs[:-1]))
    for iter_loc in locs:
        ylabs.append(utils.human_format(int(iter_loc)))

    plt.yticks(locs, ylabs)
    plt.savefig(path, transparent=True)

    plt.close(fig)

async def make_courbe(
    total_confirmed,
    total_recovered,
    total_deaths,
    is_us=False) -> Tuple[List, List]:

    timeline = list(x[:-3] for x in total_confirmed["history"].keys())
    confirmed = []
    recovered = []
    deaths = []
    active = []

    if not is_us:
        for c, r, d in zip(total_confirmed["history"],
                            total_recovered["history"],
                            total_deaths["history"]):
            try:
                confirmed.append(total_confirmed["history"][c])
                recovered.append(total_recovered["history"][r])
                deaths.append(total_deaths["history"][d])
                active.append(total_confirmed["history"][c] - total_recovered["history"][r])
            except TypeError:
                pass
    else:
        for c, d in zip(total_confirmed["history"],
                            total_deaths["history"]):
            try:
                confirmed.append(total_confirmed["history"][c])
                deaths.append(total_deaths["history"][d])
            except TypeError:
                pass
    return timeline, confirmed, recovered, deaths, active

# function to plot data from the c!graph command
async def plot_graph(path, data, graph_type, ylabel):
    # value is the name of the value to be graphed

    # the number of days to graph
    #max_days_back = 76
#
    #days_back = 10000
    #shortest = {}
    #timeline = []
    #for c in data:
    #    l = len(c['values'])
    #    if l < days_back:
    #        days_back = l
    #        shortest = c['values']
    #for s in shortest:
    #    timeline.append(s[:-3])
#
#    if days_back > max_days_back:
#        days_back = max_days_back

    timeline = data[0]['dates']
    days_back = len(timeline)
    timeline = [*range(days_back)]

    # get yvalue data from data
    values = []
    for c in data:
        p = c['values']
        p = list(map(float, p))
        values.append(p)

    # smooth curve
    for c in range(len(values)):
        ysmoothed = gaussian_filter1d(values[c], sigma=4)
        values[c] = ysmoothed
    fig, ax = plt.subplots()

    ax.spines['bottom'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)

    ax.xaxis.set_major_locator(MultipleLocator(7))
    # plot lines
    for c in range(len(values)):
        ax.plot(timeline, values[c], "-")
        

    ticks = [i for i in range(len(timeline)) if i % (days_back / 5) == 0]
    plt.xticks(ticks, ha="center")
    ax.yaxis.grid(True)
    plt.ylabel(ylabel)
    plt.xlabel("Timeline (mm/dd)")

    ax.xaxis.label.set_color('white')
    ax.yaxis.label.set_color('white')
    ax.tick_params(axis='x', colors='white')
    ax.tick_params(axis='y', colors='white')
    leg = plt.legend([c['iso3'] for c in data ], facecolor='0.1', loc="upper left")
    for text in leg.get_texts():
        text.set_color("white")
    ax.set_ylim(ymin=0)
    ylabs = []
    locs, _ = plt.yticks()

    for iter_loc in locs:
        ylabs.append(utils.human_format(iter_loc))
    plt.yticks(locs, ylabs)
    plt.savefig(path, transparent=True)

    plt.close(fig)
