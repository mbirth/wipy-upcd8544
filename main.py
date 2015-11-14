# main.py -- put your code here!

from machine import SPI, Pin

# WiPy (on Exp board, SD and User-LED jumper have to be removed!)
SPI    = machine.SPI(0)   # GP14 (CLK) + GP16 (MOSI->DIN), User-LED jumper removed!
RST    = machine.Pin('GP24')
CE     = machine.Pin('GP12')
DC     = machine.Pin('GP22')
LIGHT  = machine.Pin('GP23')
# PWR    = directly from 3V3 pin of the WiPy

import upcd8544

lcd = upcd8544.PCD8544(SPI, RST, CE, DC, LIGHT)

lcd.data([0xff])
lcd.data([0xaa, 0x55, 0xaa, 0x55, 0xaa, 0x55, 0xaa])
