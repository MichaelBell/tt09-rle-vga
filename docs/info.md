<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

A 6bpp run length encoded image or video is read from a W25Q128JV or similar QSPI flash, and output to 640x480 VGA.

This is perfect for displaying the Bad Apple music video.

![A frame from Bad Apple, rendered by the FPGA version of this design](badapple.jpg)

### Run Length Encoding

The encoding uses 16-bit words. Most words are a run length in the top 10 bits, and a colour in the bottom 6 bits.  A run must come to the end at the end of each row.

A run must be at least 2 pixels, and any group of 3 consecutive runs within a row must be at least 24 pixels, otherwise the data buffer will empty.  This could definitely be improved!

8-bit mono audio data can be interleaved into the video stream.  The PWM output value is updated by the value `0xF800 + sample`, these must be at the end of a row, but do not have to be present on every row.  With a 24MHz project clock the row clock is exactly 30kHz.

Note that row and frame repeat, which were supported on the TT07 and TT IHP 0p2 versions are not supported here because audio data is interleaved into the video data.

The data is read starting at address 0.  The special word `0xFFC0` causes the player to stop and restart from address 0 at the beginning of the next frame, restarting the video.  This could also be used to display a still image.

## How to test

Create a RLE binary file (docs/scripts to do this TBD) and load onto the flash.  The pinout matches the [QSPI Pmod](https://github.com/mole99/qspi-pmod).  This should be plugged into the [audio Pmod](https://github.com/MichaelBell/tt-audio-pmod), and then the audio Pmod plugged into the bidir pins.  Note the flash must support the h6B Fast Read Quad Output command, with 8 dummy cycles between address and data.

Connect the [Tiny VGA PMOD](https://github.com/mole99/tiny-vga) to the output pins.

Inputs 2-0 set the read latency for the SPI in half clock cycles, it's likely that will need to be set to 2 (set input 1 high and inputs 0 and 2 low).  This latency depends on the total round trip time through the mux and out to the flash and back.  Valid values are 1 to 4.

Run with a 24MHz clock.

## External hardware

* [QSPI PMOD](https://github.com/mole99/qspi-pmod)
* [Tiny VGA PMOD](https://github.com/mole99/tiny-vga)
