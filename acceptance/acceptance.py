"""
Quick and dirty test script for Micropython meant to be run on a Raspberry Pi Pico.
The script accepts commands over the REPL serial connection; these enable performing various operations on the DUT.

Note
-----
- Command "e" must be issued before any other command.
- Several commands, separated by "/", can be sent at once; e.g. "r/4" (reset, then make 4 transitions).

Pins
----
- The script is compatible with the pin assignment of the Pico at the back of the TT02 demo board.
- CLK: enabling the CLK pin in the script will generate a signal at CLOCK_FREQ_KHZ on that pin.
- SLOW_CLK: used to read the slow clock, which is required to implement the SPI interface workaround (see main README).
- DIV: connect to trigger the registration of the clock divider.

Base commands
-------------
r
    reset
k : int
    set slow clock divider
e
    enable outputs
X
    toggle pin for X2 mode
f : c | s | d  | t
    toggle SPI line (c, s, d) or tick clock (t)
s : int
    execute sequence of commands <int> (see below)
[-]int[b]
    make <int> Gray code transitions, in reverse direction if "-" is specified, starting with bouncing pulses if the suffix is "b"

Configuration word commands
---------------------------
g : bool
    set GBXEN
G : int
    set GBXTMR
w : bool
    set WRPEN
x : bool
    set UPDX2, when X2 IO pin is low (see command X)
i : int
    set INIT
M : int
    set MAX
b : bool
    set DBCEN
d
    send default configuration (that is, configuration after reset)
c : str
    set all configuration parameters from list (see format printed as "ctr:h:" when starting)
C : int
    set all configuration parameters from 32-bit numerical value

Sequences
---------
s : 1
    r/4/X/8/X/-4
s : 2
    r/M:59/g:True/G:72
"""

import sys
import uselect
import time

from machine import Pin, Timer, UART

MAX_CLOCK_FREQ_KHZ = 2.5
OUTPUT_WIDTH = 5

DELAY_CMD = 4

PINS = {
    "UART": Pin(9, mode=Pin.IN),
    "SLOW_CLK": Pin(12, mode=Pin.IN),
    "DIV": Pin(13, mode=Pin.OUT),
    "CLK": Pin(14, mode=Pin.OUT),
    "RST": Pin(15, mode=Pin.OUT),
    "GRAY": (Pin(16, mode=Pin.OUT), Pin(17, mode=Pin.OUT)),
    "X2": Pin(18, mode=Pin.OUT),
    "SPI": {
        "CS": Pin(19, mode=Pin.OUT),
        "SCK": Pin(20, mode=Pin.OUT),
        "SDI": Pin(21, mode=Pin.OUT)
    }
}


class Clock:

    freq_khz = MAX_CLOCK_FREQ_KHZ
    freq_hz = int(freq_khz * 1000)

    def __init__(self) -> None:
        
        if "CLK" in PINS.keys():
            f = int(MAX_CLOCK_FREQ_KHZ * 1000)
            print(f"clk:{f}")
            pin_clk = PINS["CLK"]
            timer = Timer(mode=Timer.PERIODIC, freq=2*f, callback=lambda v: pin_clk.value(not pin_clk.value()))

    @staticmethod
    def set_freq(f_hz: int):
        Clock.freq_hz = f_hz
        Clock.freq_khz = f_hz / 1000
        print(f"frq:{Clock.freq_hz},{Clock.freq_khz}")

    @staticmethod
    def cycles_to_ms(cycles: int) -> int:
        return int(cycles / Clock.freq_khz)

    @staticmethod
    def set_slow_clock_divider(div: int):

        PINS["DIV"].low()

        Clock.set_freq(int(Clock.freq_hz / (div + 1)))

        for p in  [
            PINS["CLK"],
            PINS["RST"],
            PINS["GRAY"][0],
            PINS["GRAY"][1],
            PINS["X2"],
            PINS["SPI"]["CS"],
            PINS["SPI"]["SCK"],
            PINS["SPI"]["SDI"]
        ]:
            p.value(div & 1)
            div >>= 1

        time.sleep_ms(1)
        PINS["DIV"].high()


class ConfigurationPort:

    COUNTER_DEFAULT_MAX_VALUE = (1 << OUTPUT_WIDTH) - 1
    COUNTER_DEFAULT_VALUE = 0

    DECODER_DEFAULT_DEBOUNCE = True
    DECODER_DEFAULT_WRAP = False
    DECODER_DEFAULT_X1_VALUE = 0b00
    DECODER_DEFAULT_FORCE_X2 = False

    GEARBOX_DEFAULT_ENABLED = False
    GEARBOX_DEFAULT_ENCODER = (24, 4)

    SPI_WORD_LEN = 8
    SPI_WORDS = 4

    GEARBOX_SHIFT = 3

    def __init__(self, bus) -> None:

        # Use bit banging as the Pico SPI module is not slow enough
        self.cs = bus["CS"]
        self.sck = bus["SCK"]
        self.sdi = bus["SDI"]
        self.cs.low()
        self.sck.low()
        self.sdi.low()

        print(f"cfg:h:ctr_init,ctr_max,dbnc,wrap,x1,x2,gbx_en,gbx_parm")

        gbp_sec, gbp_cycles = self.get_timer_period(*ConfigurationPort.GEARBOX_DEFAULT_ENCODER, Clock.freq_hz)

        # Map contains the parameters of calculate_parameters_value()
        self.default_conf = {
            "debounce": ConfigurationPort.DECODER_DEFAULT_DEBOUNCE,
            "wrap": ConfigurationPort.DECODER_DEFAULT_WRAP,
            "x1_value": ConfigurationPort.DECODER_DEFAULT_X1_VALUE,
            "force_x2": ConfigurationPort.DECODER_DEFAULT_FORCE_X2,
            "gearbox": ConfigurationPort.GEARBOX_DEFAULT_ENABLED,
            "gearbox_timer_cycles": gbp_cycles,
            "max_value": ConfigurationPort.COUNTER_DEFAULT_MAX_VALUE,
            "init_value": ConfigurationPort.COUNTER_DEFAULT_VALUE
        }

        self.current_conf = self.default_conf.copy()

        # Just to print command format
        self.calculate_parameters_value(**self.current_conf)

    def enable(self):

        # TODO: is this needed to bring CS to a consistent state?
        self.cs.high()
        self.sync_set(self.cs, False)
        self.sync_set(self.cs, True)

        self.sck.low()
        self.sdi.low()

    @staticmethod
    def get_timer_period(detents: int, transitions: int, clock: int):

        # Period is chosen so that gear value 2 would be reached after 1s at constant 1 turn per second
        # Shift is chosen to keep period close to 1 / (D * P) with 24 detents / 24 PPR encoder

        # For
        g = 2   # Gear
        d = 1   # Duration in s
        f = 2 ** ConfigurationPort.GEARBOX_SHIFT

        # Solve ((detents * transitions * d) - (d / p)) / f = g for p
        p = 1 / (detents * transitions - g * f / d)

        return p, int(round(p * Clock.freq_hz))

    @staticmethod
    def calculate_parameters_value(
            wrap: bool, debounce: bool, gearbox: bool, force_x2: bool,
            x1_value: int, gearbox_timer_cycles: int, init_value: int, max_value: int):

        print(f"cfg:p:{init_value},{max_value},{debounce},{wrap},{x1_value},{force_x2},{gearbox},{gearbox_timer_cycles}")

        res = int(gearbox) |\
               (int(wrap) << 1) |\
               (int(debounce) << 2) |\
               (x1_value << 3) | \
               (int(force_x2) << 5) |\
               (gearbox_timer_cycles << ConfigurationPort.SPI_WORD_LEN) |\
               (init_value << (ConfigurationPort.SPI_WORD_LEN * 2)) |\
               (max_value << (ConfigurationPort.SPI_WORD_LEN * 3))
        
        print(f"cfg:x:0x{res:x}")

        return res

    def sync_set(self, p: Pin, val: bool):

        slow_clk = PINS["SLOW_CLK"]

        while slow_clk.value() == 0:
            pass
        while slow_clk.value() == 1:
            pass

        p.value(val)

    def send(self, words: int):

        self.sck.low()

        self.sync_set(self.cs, False)
        time.sleep_us(1000)

        w = self.SPI_WORD_LEN * self.SPI_WORDS
        msk = 1 << (w - 1)

        for i in range(32):

            self.sdi.value(words & msk)
            words <<= 1
    
            self.sync_set(self.sck, True)
            self.sync_set(self.sck, False)

        self.sync_set(self.cs, True)

    def send_current_conf(self):

        self.send(self.calculate_parameters_value(**self.current_conf))

    def update_to_defaults(self):

        self.current_conf = self.default_conf.copy()
        self.send_current_conf()

    def update_from_cmd(self, cmd: str):

        w = cmd.split(",")
        assert len(w) == 8, "invalid number of parameters" 

        ctr_init, ctr_max, dbnc, wrap, x1, x2, gbx_en, gbx_timer = w

        self.current_conf = {
            "debounce": eval(dbnc),
            "wrap": eval(wrap),
            "x1_value": int(x1),
            "force_x2": eval(x2),
            "gearbox": eval(gbx_en),
            "gearbox_timer_cycles": int(gbx_timer),
            "max_value": int(ctr_max),
            "init_value": int(ctr_init)
        }

        self.send_current_conf()

    def update_from_value(self, val: int):

        # Current config is not updated
        self.send(val)

    def set(self, param: str, val: str):
        
        v = eval(val)
        assert type(self.current_conf[param]) == type(v), "invalid parameter type"

        self.current_conf[param] = v
        self.send_current_conf()

    def toggle(self, pin: str):

        if pin == "t":
            self.sync_set(self.sck, True)
            self.sync_set(self.sck, False)

        else:
            p = {
                "c": self.cs,
                "s": self.sck,
                "d": self.sdi
            }[pin]

            self.sync_set(p, not p.value())


class Encoder:

    CYCLES = 4
    # DURATION_MS = 500 // (ConfigurationPort.GEARBOX_DEFAULT_ENCODER[0] * ConfigurationPort.GEARBOX_DEFAULT_ENCODER[1]) * 12

    BOUNCE_US = 800
    BOUNCE_COUNT = 2

    def __init__(self, pins: list[int]) -> None:

        self.out_a = Pin(pins[0], Pin.OUT)
        self.out_b = Pin(pins[1], Pin.OUT)
        self.set(0)

    def __set_io(self, val: int):

        self.out_a.value(val & 1)
        self.out_b.value(val >> 1)

    def set(self, val: int) -> None:

        self.val = val & 3
        self.__set_io(self.val)
        # print(f"val:{self.val}")

    def tick(self, count: int = 1, bounce: bool = False) -> int:

        dir = count >= 0

        for c in range(abs(count)):
            time.sleep_ms(Clock.cycles_to_ms(self.CYCLES))

            nxt = ([1, 3, 0, 2] if dir else [2, 0, 3, 1])[self.val]

            for b in range(self.BOUNCE_COUNT if bounce else 0):
                self.__set_io(nxt)
                time.sleep_us(self.BOUNCE_US)
                self.__set_io(self.val)
                time.sleep_us(self.BOUNCE_US)

            self.set(nxt)

        return self.val
    
    def bounce(self, delay: int, count: int = 3):
        pass


class SignalAsserter:
    def __init__(self, pin: int) -> None:

        self.pin = Pin(pin, Pin.OUT)
        self.pin.low()

    def do_assert(self, ms: int = 10):

        self.pin.high()
        time.sleep_ms(ms)
        self.pin.low()


def handle_serial_data():
    print("serial")


Clock.set_slow_clock_divider(div=0)
# sys.stdin.readline()

enc = Encoder(pins=PINS["GRAY"])
rst = SignalAsserter(pin=PINS["RST"])
conf = ConfigurationPort(bus=PINS["SPI"])

pin_x2 = PINS["X2"]

pin_led = Pin("LED", Pin.OUT)
pin_led.high()

uart = UART(1, baudrate=Clock.freq_hz, bits=8, parity=None, stop=1, rx=PINS["UART"], timeout=1)

spoll = uselect.poll()
spoll.register(sys.stdin, uselect.POLLIN)
spoll.register(uart, uselect.POLLIN)

# TODO: move to ConfigurationPort
cmd_conf = {
    "M": "max_value",
    "i": "init_value",
    "x": "force_x2",
    "w": "wrap",
    "b": "debounce",
    "g": "gearbox",
    "G": "gearbox_timer_cycles"
}

enabled = False
while True:

    pend = spoll.poll()

    if pend[0][0] == uart:
        v = int(uart.read(1)[0])
        print(f"ser:{v}")
        continue

    commands = sys.stdin.readline()
    commands = commands.strip()

    if commands != "" and commands[0] == "s":
        commands = {
            "1": "r/4/X/8/X/-4",
            "2": "r/M:59/g:True/G:72"
        }[commands[2:]]

    for cmd in commands.split("/"):
        try:
            if cmd == "":
                continue

            if cmd == "e":
                conf.enable()
                enc.set(0)
                pin_x2.low()
                enabled = True
                print("enb:True")
                continue

            if not enabled:
                print("enb:False")
                continue

            cmd = cmd.strip()
            print(f"cmd:{cmd}")

            # Reset
            if cmd == "r":
                # enc.set(0)
                rst.do_assert(Clock.cycles_to_ms(4))

            # Toggle pin forcing x2 mode 
            elif cmd == "X":
                pin_x2.value(not pin_x2.value())
                print(f"x2:{pin_x2.value()}")

            # Set all configuration parameters from list
            elif cmd[0] == "c":
                conf.update_from_cmd(cmd[2:])

            # Set all configuration parameters from 32-bit numerical value
            elif cmd[0] == "C":
                conf.update_from_value(int(cmd[2:], 0))

            # Restore all configuration parameters to the default value
            elif cmd[0] == "d":
                conf.update_to_defaults()

            # Set slow clock divider
            elif cmd[0] == "k":
                Clock.set_slow_clock_divider(int(cmd[2:]))

            # Toggle SPI line or tick clock
            elif cmd[0] == "f":
                conf.toggle(cmd[2])

            # Set configuration parameters (see table above)
            elif cmd[0] in cmd_conf.keys():
                conf.set(cmd_conf[cmd[0]], cmd[2:])

            # Make Gray code transitionsddd
            else:
                bounce = cmd[-1] == "b"
                val = int(cmd[:-1] if bounce else cmd)
                enc.tick(val, bounce=bounce)

        except ValueError as e:
            print(f"err:{e.__class__.__name__}:{e}")
            continue

        pin_led.value(not pin_led.value())

        time.sleep_ms(DELAY_CMD)
