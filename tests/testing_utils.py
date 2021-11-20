import os
import contextlib


def areTheSameFiles(fn1, fn2, fileHandler, *args):
    """
    Tests that files contain the same data

    If fileHandler is a textgrid file reader like
    textgrid.openTextgrid then we can compare
    a shortTextgrid and a longTextgrid.

    If fileHandler is readFile or io.open, etc then the raw
    text will be compared.
    """
    data1 = fileHandler(fn1, *args)
    data2 = fileHandler(fn2, *args)

    return data1 == data2


def supressStdout(func):
    # https://stackoverflow.com/a/28321717/3787959
    def wrapper(*a, **ka):
        with open(os.devnull, "w") as devnull:
            with contextlib.redirect_stdout(devnull):
                func(*a, **ka)

    return wrapper
