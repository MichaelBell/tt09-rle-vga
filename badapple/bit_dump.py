#!/usr/bin/env python3

import sys
import struct
from PIL import Image

out_file = open("badapple640x480.bin", "wb")
music = open("badapple.wav", "rb")

# Discard header
music.read(0xca)

samples = []
last_sample = -256
rows = 1

TWO = 2
FOUR = 4

colour_shift_changes = {
    1: TWO,
    512: FOUR,
    760: TWO,
    1705: FOUR,
    1873: TWO,
    1913: FOUR,
    2113: TWO,
    2606: FOUR,
    #2832: TWO,
    3320: FOUR,
    3472: TWO,
    3820: FOUR,
    3875: TWO,
    3968: FOUR,
    4030: TWO,
    4230: FOUR,
    4345: TWO,
    4410: FOUR,
    4442: TWO,
    5040: FOUR,
    5100: TWO,
    5212: FOUR,
    5289: TWO,
    5350: FOUR,
    5647: TWO,
    5910: FOUR,
    5973: TWO,
    6520: FOUR
}


max_span_len = 4
data_len = 0
colour_shift = TWO
last_colour = -1
row_out = False
skipped_audio = False

for f in range(2,6957*2):
#for f in range(2,1000):
    i = f // 2
    img = Image.open("frames/badapple%04d.png" % (i,)).resize((640,480))

    data = img.load()
    last_spans = []
    repeat_count = 0

    if i in colour_shift_changes.keys():
        colour_shift = colour_shift_changes[i]

    for y in range(0,500):
        if y < 480:
            spans = []
            span_len = 0
            span_colour = 0
            for x in range(640):
                if colour_shift == FOUR:
                    if data[x, y][0] > 170: colour =   0b111111
                    elif data[x, y][0] > 100: colour = 0b101010
                    elif data[x, y][0] > 45: colour =  0b010101
                    else: colour = 0
                else:
                    if data[x, y][0] > 100: colour =   0b111111
                    else: colour = 0

                if colour != span_colour:
                    if span_len > 1:
                        spans.append([span_len, span_colour])
                        span_len = 0
                    span_colour = colour

                span_len += 1

            if span_len > 1:
                spans.append([span_len, span_colour])
            else:
                spans[-1][0] += 1

            if len(spans) > 3:
                while True:
                    shortest_spans = 640
                    shortest_idx = 0
                    for idx, s in enumerate(spans[1:-1]):
                        slen = s[0] + spans[idx][0] + spans[idx+2][0]

                        if slen < shortest_spans:
                            shortest_idx = idx + 1
                            shortest_spans = slen
                
                    if shortest_spans >= 3 * max_span_len:
                        break

                    shortest_span, idx = min((a, i) for (i, a) in enumerate([s[0] for s in spans[shortest_idx-1:shortest_idx+2]]))
                    shortest_idx += idx - 1

                    #print(shortest_span, shortest_idx, spans)
                    if shortest_idx == 0: 
                        spans[1][0] += shortest_span
                        del spans[0]
                    elif shortest_idx == len(spans) - 1: 
                        spans[-2][0] += shortest_span
                        del spans[-1]
                    else:
                        if spans[shortest_idx-1][0] < spans[shortest_idx+1][0]:
                            spans[shortest_idx-1][0] += shortest_span
                            del spans[shortest_idx]
                        else:
                            spans[shortest_idx+1][0] += shortest_span
                            del spans[shortest_idx]
                        if spans[shortest_idx][1] == spans[shortest_idx-1][1]:
                            spans[shortest_idx-1][0] += spans[shortest_idx][0]
                            del spans[shortest_idx]

                    if len(spans) <= 3:
                        break

            if len(spans) > 1 or spans[0][1] != last_colour or rows != 1:
                if sum([s[0] for s in spans]) != 640:
                    #print(spans)
                    print("Error")
                    sys.exit(0)

                for span in spans:
                    out_file.write(struct.pack('>H', (span[0] << 6) + span[1]))
                data_len += 2 * len(spans)
                last_colour = spans[-1][1]
                row_out = True
            else:
                row_out = False
        else:
            row_out = False

        rows -= 1
        if rows != 0: continue

        while len(samples) < 4:
            val = music.read(1)
            if val is None or len(val) < 1: break
            samples.append(struct.unpack("B", val)[0])
        
        if len(samples) < 4: break
        
        differences = [samples[0] - last_sample]
        for j in range(1,4):
            differences.append(samples[j] - samples[j-1])
        dmax = max([d if d >= 0 else -1-d for d in differences])
        
        if y < 479 and differences[0] == 0 and row_out:
            rows = 1
            samples = samples[1:]
            skipped_audio = True
            continue
        skipped_audio = False
        
        if dmax < 4:
            differences = [d & 7 for d in differences]
            val = (differences[0] << 9) | (differences[1] << 6) | (differences[2] << 3) | differences[3]
            out_file.write(struct.pack(">H", 0xF000 + val))
            last_sample = samples[3]
            samples = []
            rows = 4
            
        elif dmax < 8:
            differences = [d & 0xf for d in differences]
            val = (differences[0] << 8) | (differences[1] << 4) | differences[2]
            out_file.write(struct.pack(">H", 0xE000 + val))
            last_sample = samples[2]
            samples = samples[3:]
            rows = 3
        
        elif dmax < 32:
            differences = [d & 0x3f for d in differences]
            val = (differences[0] << 6) | differences[1]
            out_file.write(struct.pack(">H", 0xD000 + val))
            last_sample = samples[1]
            samples = samples[2:]
            rows = 2
        
        else:
            out_file.write(struct.pack(">H", 0xC000 + samples[0]))
            last_sample = samples[0]
            samples = samples[1:]
            rows = 1
            
        data_len += 2

    #if repeat_count != 0:
    #    out_file.write(struct.pack('>H', 0xf800 + repeat_count))
    #    data_len += 2
    print("Frame %d, len %.2fMB" % (i, data_len / (1024 * 1024)))

    if data_len > 16 * 1024 * 1024 - 32 * 1024:
        print("Terminating early")
        break

out_file.write(struct.pack('>H', (0x2ff << 6)))
out_file.close()
