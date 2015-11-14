# -*- coding: utf-8 -*- 
"""
MicroPython PCD8544 driver
(for Nokia 5110 displays)
"""

__author__     = "Markus Birth"
__copyright__  = "Copyright 2015, Markus Birth"
__credits__    = ["Markus Birth"]
__license__    = "MIT"
__version__    = "1.0"
__maintainer__ ="Markus Birth"
__email__      = "markus@birth-online.de"
__status__     = "Production"

# Datasheet: https://www.sparkfun.com/datasheets/LCD/Monochrome/Nokia5110.pdf
# Inspiration from:
#   - https://github.com/inaugurator/upyd5110
#   - https://github.com/rm-hull/pcd8544/blob/master/src/lcd.py
#
# PINOUT
# WiPy/pyBoard      display   function
#
# 3V3 or any Pin => VCC       3.3V logic voltage (0=off, 1=on)
# MOSI           => DIN       data flow (Master out, Slave in)
# SCK            => CLK       SPI clock
# any Pin        => RST       Reset pin (0=reset, 1=normal)
# any Pin        => CE        Chip Enable (0=listen for input, 1=ignore input)
# any Pin        => DC        Data/Command (0=commands, 1=data)
# any Pin        => LIGHT     Light (0=on, 1=off)
# GND            => GND
#
# pyBoard "Y" side
# SPI    = pyb.SPI(1)
# RST    = pyb.Pin('Y4')
# CE     = pyb.Pin('Y5')
# DC     = pyb.Pin('Y3')
# LIGHT  = pyb.Pin('Y2')
# PWR    = pyb.Pin('Y1')
#
# pyBoard "X" side
# SPI    = pyb.SPI(2)
# RST    = pyb.Pin('X4')
# CE     = pyb.Pin('X5')
# DC     = pyb.Pin('X3')
# LIGHT  = pyb.Pin('X2')
# PWR    = pyb.Pin('X1')
#
# WiPy (on Exp board, SD and User-LED jumper have to be removed!)
# SPI    = machine.SPI(0)   # GP14 (CLK) + GP16 (MOSI->DIN), User-LED jumper removed!
# RST    = machine.Pin('GP24')
# CE     = machine.Pin('GP12')
# DC     = machine.Pin('GP22')
# LIGHT  = machine.Pin('GP23')
# PWR    = directly from 3V3 pin of the WiPy

try:
    import pyb as machine
except:
    # WiPy
    import machine

import struct
import time

class PCD8544:
    def __init__(self, spi, rst, ce, dc, light, pwr=None):
        self.width  = 84
        self.height = 48

        # init the SPI bus and pins
        spi.init(spi.MASTER, baudrate=328125, bits=8, polarity=0, phase=1, firstbit=spi.MSB)
        if "OUT_PP" in dir(rst):
            # pyBoard style
            rst.init(rst.OUT_PP, rst.PULL_NONE)  # Reset line
            ce.init(ce.OUT_PP, ce.PULL_NONE)     # Chip Enable
            dc.init(dc.OUT_PP, dc.PULL_NONE)     # Data(1) / Command(0) mode
            light.init(light.OUT_PP, light.PULL_NONE)
            if pwr:
                pwr.init(pwr.OUT_PP, pwr.PULL_NONE)
        else:
            # WiPy style
            rst.init(rst.OUT, None)
            ce.init(ce.OUT, None)
            dc.init(dc.OUT, None)
            light.init(light.OUT, None)
            if pwr:
                pwr.init(pwr.OUT, None)

        self.spi   = spi
        self.rst   = rst
        self.ce    = ce
        self.dc    = dc
        self.light = light
        self.pwr   = pwr

        self.light_off()
        self.power_on()
        self.ce.value(1)  # set chip to disable (don't listen to input)
        self.reset()
        self.set_contrast(0xba)
        self.clear()

    def set_contrast(self, value):
        """ set LCD voltage, i.e. contrast """
        assert 0x80 <= value <= 0xff, "contrast value must be between 0x80 and 0xff"
        self.command([0x21, 0x06, 0x14, value, 0x20, 0x0c])
        # 0x21 - enter extended instruction set (H=1)
        # 0x06 - set temperature coefficient 2
        # 0x14 - set BIAS system to n=3 (recomm. mux rate 1:40/1:34)
        # value - (80-ff) - set Vop (80 = 3.00V, ff = 10.68V), 8b seems to work (0x3b/d70: 3.00+(70*0.06)=7.2V)
        # 0x20 - back to basic instruction set
        # 0x0c - normal display mode

    def position(self, x, y):
        """ set cursor to bank y, column x """
        assert 0 <= x < self.width, "x must be between 0 and 83"
        assert 0 <= y < self.height // 8, "y must be between 0 and 5"
        self.command([x + 0x80, y + 0x40])

    def clear(self):
        """ clear screen """
        self.position(0, 0)
        self.data([0] * (self.height * self.width // 8))
        self.position(0, 0)

    def sleep_ms(self, mseconds):
        try:
            time.sleep_ms(mseconds)
        except AttributeError:
            machine.delay(mseconds)

    def sleep_us(self, useconds):
        try:
            time.sleep_us(useconds)
        except AttributeError:
            machine.udelay(useconds)

    def power_on(self):
        if self.pwr:
            self.pwr.value(1)
        self.reset()

    def reset(self):
        """ issue reset impulse to reset the display """
        self.rst.value(0)  # RST on
        self.sleep_us(100) # reset impulse has to be >100 ns and <100 ms
        self.rst.value(1)  # RST off

    def power_off(self):
        self.clear()
        self.command([0x20, 0x08])
        # 0x20 - basic instruction set
        # 0x08 - set display to blank (doesn't delete contents)
        self.sleep_ms(10)
        if self.pwr:
            self.pwr.value(0) # turn off power

    def command(self, arr):
        """ send bytes in command mode """
        self.bitmap(arr, 0)

    def data(self, arr):
        """ send bytes in data mode """
        self.bitmap(arr, 1)

    def bitmap(self, arr, dc):
        self.dc.value(dc)
        buf = struct.pack('B'*len(arr), *arr)
        self.ce.value(0) # set chip to listening/enable
        try:
            self.spi.send(buf)
        except AttributeError:
            self.spi.write(buf)
        self.ce.value(1) # set chip to disable

    def light_on(self):
        self.light.value(0)  # pull to GND

    def light_off(self):
        self.light.value(1)  # set to HIGH
