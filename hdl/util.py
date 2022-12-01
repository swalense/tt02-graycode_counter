import math
import numpy as np


def max_for_bits(bits: int):
    return (1 << bits) - 1


def bits_multiple(bits, multiple_of=8):
    return int(math.ceil(bits / multiple_of) * multiple_of)


def bits_required(v: int):
    m = np.max(np.abs(v))
    return int(np.log2(np.floor(m))) + 1 if m >= 1 else 0
