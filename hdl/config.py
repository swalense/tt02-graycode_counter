
import hdl.util as util

CLOCK_FREQ = 5e3

COUNTER_WIDTH = 8
OUTPUT_WIDTH = 5

COUNTER_DEFAULT_MAX_VALUE = util.max_for_bits(OUTPUT_WIDTH)
COUNTER_DEFAULT_VALUE = 0

DECODER_DEFAULT_DEBOUNCE = True
DECODER_DEFAULT_WRAP = False
DECODER_DEFAULT_X1_VALUE = 0b00
DECODER_DEFAULT_FORCE_X2 = False

GEARBOX_DEFAULT_ENABLED = False
GEARBOX_DEFAULT_ENCODER = (24, 4)

UART_WORD_LEN = COUNTER_WIDTH
assert UART_WORD_LEN >= COUNTER_WIDTH

# Keep transmitter idle after stop bit
UART_IDLE_CYCLES = 4

# This cannot be smaller than 8 to accommodate the gearbox parameter
SPI_WORD_LEN = 8
