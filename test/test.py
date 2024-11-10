# SPDX-FileCopyrightText: © 2024 Michael Bell
# SPDX-License-Identifier: MIT

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge, Timer


@cocotb.test()
async def test_sync(dut):
    dut._log.info("Start")

    # Set the clock period to 40 ns (25 MHz)
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    dut.ui_in.value = 0
    for i in range(5):
        dut.spi_miso_buf[i].value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 2)
    assert dut.uio_oe.value == 0
    await ClockCycles(dut.clk, 2)
    dut.rst_n.value = 1

    dut._log.info("Test sync")

    await Timer(1, "ns")
    assert dut.uio_oe.value == 0b11001001

    await ClockCycles(dut.clk, 1)

    for i in range(16):
        vsync = 1 if i in (3, 4, 5, 6) else 0
        for j in range(16):
            assert dut.vsync.value == vsync
            assert dut.hsync.value == 1
            await ClockCycles(dut.clk, 1)
        for j in range(64):
            assert dut.vsync.value == vsync
            assert dut.hsync.value == 0
            await ClockCycles(dut.clk, 1)
        for j in range(80+640):
            assert dut.vsync.value == vsync
            assert dut.hsync.value == 1
            await ClockCycles(dut.clk, 1)

async def expect_read_cmd(dut, addr):
    assert dut.spi_cs.value == 1
    await FallingEdge(dut.spi_cs)

    assert dut.spi_mosi.value == 0
    
    cmd = 0x6B
    for i in range(8):
        await ClockCycles(dut.spi_clk, 1)
        assert dut.spi_mosi.value == (1 if cmd & 0x80 else 0)
        assert dut.spi_cs.value == 0
        assert dut.uio_oe.value == (0b11000111 if dut.qspi_sel.value else 0b11001011)
        cmd <<= 1

    for i in range(24):
        await ClockCycles(dut.spi_clk, 1)
        assert dut.spi_mosi.value == (1 if addr & 0x800000 else 0)
        assert dut.spi_cs.value == 0
        assert dut.uio_oe.value == (0b11000111 if dut.qspi_sel.value else 0b11001011)
        addr <<= 1

    for i in range(8):
        await ClockCycles(dut.spi_clk, 1)
        assert dut.spi_cs.value == 0
        assert dut.uio_oe.value == (0b11000011 if dut.qspi_sel.value else 0b11001001)

    await FallingEdge(dut.spi_clk)

def spi_send_rle(dut, length, colour, latency):
    data = (length << 6) + colour

    return spi_send_data(dut, data, latency)

async def spi_send_data(dut, data, latency):
    assert dut.spi_cs.value == 0

    for i in range(4):
        await Timer(1, "ns")
        dut.spi_miso_buf[0].value = (data >> 12) & 0xF
        assert dut.uio_oe.value == (0b11000011 if dut.qspi_sel.value else 0b11001001)
        assert dut.spi_cs.value == 0
        await FallingEdge(dut.spi_clk)
        data <<= 4

async def generate_colours(dut, frames, latency=1):
    dut.latency.value = latency
    for f in range(frames):
        await expect_read_cmd(dut, 0)
        addr = 0

        for colour in range(64):
            await spi_send_rle(dut, 320, colour, latency)
            await spi_send_rle(dut, 2, 1, latency)
            await spi_send_rle(dut, 2, 2, latency)
            await spi_send_rle(dut, 316, colour, latency)
        addr += 8 * 64

        colour = 20
        for i in range(2, 640, 2):
            await spi_send_rle(dut, i, colour, latency)
            colour += 1
            if colour == 64: colour = 0
            await spi_send_rle(dut, 640-i, colour, latency)
            colour += 1
            if colour == 64: colour = 0
        addr += 4 * 319

        for i in range(480-64-319):
            for j in range(640//8):
                await spi_send_rle(dut, 8, j & 0x3f, latency)

        await spi_send_rle(dut, 0x2ff, 0, latency)
        await RisingEdge(dut.spi_cs)

@cocotb.test()
async def test_colour(dut):
    dut._log.info("Start")

    # Set the clock period to 40 ns (25 MHz)
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    dut.ui_in.value = 0
    for i in range(5):
        dut.spi_miso_buf[i].value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1

    colour_gen = cocotb.start_soon(generate_colours(dut, 3))

    await ClockCycles(dut.hsync, 1)

    for i in range(3):
        await ClockCycles(dut.hsync, 3+4+13)

        for colour in range(64):
            await ClockCycles(dut.clk, 81)
            for i in range(320):
                assert dut.colour.value == colour
                await ClockCycles(dut.clk, 1)
            for i in range(2):
                assert dut.colour.value == 1
                await ClockCycles(dut.clk, 1)
            for i in range(2):
                assert dut.colour.value == 2
                await ClockCycles(dut.clk, 1)
            for i in range(316):
                assert dut.colour.value == colour
                await ClockCycles(dut.clk, 1)
            await ClockCycles(dut.hsync, 1)

        colour = 20
        for i in range(2, 640, 2):
            await ClockCycles(dut.clk, 81)
            for j in range(640):
                assert dut.colour.value == (colour if j < i else colour + 1)
                await ClockCycles(dut.clk, 1)
            await ClockCycles(dut.hsync, 1)
            colour += 2
            if colour == 64: colour = 0

        for i in range(64+319, 480):
            await ClockCycles(dut.clk, 81)
            for j in range(640//8):
                for k in range(8):
                    assert dut.colour.value == j & 0x3f
                    await ClockCycles(dut.clk, 1)
            await ClockCycles(dut.hsync, 1)

    await colour_gen

@cocotb.test()
async def test_latency(dut):
    dut._log.info("Start")

    # Set the clock period to 40 ns (25 MHz)
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())

    for lat in range(1, 5):
        # Reset
        dut._log.info(f"Reset, latency {lat}")
        dut.ena.value = 1
        dut.ui_in.value = lat
        for i in range(5):
            dut.spi_miso_buf[i].value = 0
        dut.rst_n.value = 0
        await ClockCycles(dut.clk, 10)
        dut.rst_n.value = 1

        colour_gen = cocotb.start_soon(generate_colours(dut, 2, lat))

        await ClockCycles(dut.hsync, 1)

        for i in range(2):
            await ClockCycles(dut.hsync, 3+4+13)

            for colour in range(64):
                await ClockCycles(dut.clk, 81)
                for i in range(320):
                    assert dut.colour.value == colour
                    await ClockCycles(dut.clk, 1)
                for i in range(2):
                    assert dut.colour.value == 1
                    await ClockCycles(dut.clk, 1)
                for i in range(2):
                    assert dut.colour.value == 2
                    await ClockCycles(dut.clk, 1)
                for i in range(316):
                    assert dut.colour.value == colour
                    await ClockCycles(dut.clk, 1)
                await ClockCycles(dut.hsync, 1)

            colour = 20
            for i in range(2, 640, 2):
                await ClockCycles(dut.clk, 81)
                for j in range(640):
                    assert dut.colour.value == (colour if j < i else colour + 1)
                    await ClockCycles(dut.clk, 1)
                await ClockCycles(dut.hsync, 1)
                colour += 2
                if colour == 64: colour = 0

            for i in range(64+319, 480):
                await ClockCycles(dut.clk, 81)
                for j in range(640//8):
                    for k in range(8):
                        assert dut.colour.value == j & 0x3f
                        await ClockCycles(dut.clk, 1)
                await ClockCycles(dut.hsync, 1)

        await colour_gen

async def generate_audio(dut, frames, latency=1):
    dut.latency.value = latency
    for f in range(frames):
        await expect_read_cmd(dut, 0)
        addr = 0

        for colour in range(64):
            if (colour & 1) == 0:
                await spi_send_rle(dut, 320, colour, latency)
                await spi_send_rle(dut, 2, 1, latency)
                await spi_send_rle(dut, 2, 2, latency)
                await spi_send_rle(dut, 316, 63 - colour, latency)
            await spi_send_data(dut, 0xC000 + colour, latency)
        addr += 8 * 64

        colour = 20
        for i in range(2, 640, 2):
            await spi_send_rle(dut, i, colour, latency)
            colour += 1
            if colour == 64: colour = 0
            await spi_send_rle(dut, 640-i, colour, latency)
            colour += 1
            if colour == 64: colour = 0
            if (i % 6) == 2:
                await spi_send_data(dut, 0xE6A0, latency)
        addr += 4 * 319

        for i in range(480-64-319):
            for j in range(640//4):
                await spi_send_rle(dut, 4, j & 0x3f, latency)
            if (i % 4) == 2:
                await spi_send_data(dut, 0xF000 + i, latency)

        await spi_send_data(dut, 0xD000, latency)
        await spi_send_rle(dut, 0x2ff, 0, latency)
        await spi_send_rle(dut, 640, 0x3f, latency)
        await spi_send_rle(dut, 640, 0x3f, latency)
        await RisingEdge(dut.spi_cs)

@cocotb.test()
async def test_audio(dut):
    dut._log.info("Start")

    # Set the clock period to 40 ns (25 MHz)
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    dut.ui_in.value = 9
    dut.spi_miso_buf[0].value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1

    colour_gen = cocotb.start_soon(generate_audio(dut, 3))

    await ClockCycles(dut.hsync, 1)

    for i in range(2):
        await ClockCycles(dut.hsync, 3+4+13)

        for colour in range(64):
            await ClockCycles(dut.clk, 81)
            if (colour & 1) == 0:
                for i in range(320):
                    assert dut.colour.value == colour
                    await ClockCycles(dut.clk, 1)
                for i in range(2):
                    assert dut.colour.value == 1
                    await ClockCycles(dut.clk, 1)
                for i in range(2):
                    assert dut.colour.value == 2
                    await ClockCycles(dut.clk, 1)
                for i in range(316):
                    assert dut.colour.value == 63 - colour
                    await ClockCycles(dut.clk, 1)
            else:
                for i in range(640):
                    assert dut.colour.value == 64 - colour
                    await ClockCycles(dut.clk, 1)
            await ClockCycles(dut.hsync, 1)

        colour = 20
        for i in range(2, 640, 2):
            await ClockCycles(dut.clk, 81)
            for j in range(640):
                assert dut.colour.value == (colour if j < i else colour + 1)
                await ClockCycles(dut.clk, 1)
            await ClockCycles(dut.hsync, 1)
            colour += 2
            if colour == 64: colour = 0

        for i in range(64+319, 480):
            await ClockCycles(dut.clk, 81)
            for j in range(640//4):
                for k in range(4):
                    assert dut.colour.value == j & 0x3f
                    await ClockCycles(dut.clk, 1)
            await ClockCycles(dut.hsync, 1)

    await ClockCycles(dut.hsync, 3+4+14)

    for colour in range(64):
        await ClockCycles(dut.clk, 2)
        count = 0
        for i in range(255):
            count += dut.pwm.value
            await ClockCycles(dut.clk, 1)
        assert count == colour
        await ClockCycles(dut.hsync, 1)

    sample = 63
    for i in range(2, 640, 6):
        await ClockCycles(dut.clk, 2)
        count = 0
        for i in range(255):
            count += dut.pwm.value
            await ClockCycles(dut.clk, 1)
        assert count == sample + 6
        await ClockCycles(dut.hsync, 1)
        for j in range(2):
            await ClockCycles(dut.clk, 2)
            count = 0
            for i in range(255):
                count += dut.pwm.value
                await ClockCycles(dut.clk, 1)
            assert count == sample
            await ClockCycles(dut.hsync, 1)

    for i in range(2, 480-64-319, 4):
        diff = [(i >> 9) & 7, (i >> 6) & 7, (i >> 3) & 7, i & 7]
        for j in range(4):
            if diff[j] >= 4: diff[j] -= 8
            sample += diff[j]
            sample &= 0xFF
            await ClockCycles(dut.clk, 2)
            count = 0
            for i in range(255):
                count += dut.pwm.value
                await ClockCycles(dut.clk, 1)
            assert count == sample
            await ClockCycles(dut.hsync, 1)

    await colour_gen

