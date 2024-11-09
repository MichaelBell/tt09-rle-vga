#!/usr/bin/env python3

import sys
import struct
from PIL import Image

out_file = open("steamw640x480.bin", "wb")
music = open("steamw.wav", "rb")

# Discard header
music.read(0x4e)

samples = []
last_sample = -256
rows = 1

TWO = 2
FOUR = 4

colour_shift_changes = {
    1: TWO,
    780: TWO
}

max_span_len = 4
data_len = 0
colour_shift = TWO

# Discard 609 frames of audio
for i in range(1,610):
    music.read(500)

#for f in range(2,6957*2):
for i in range(610,5000):
    img = Image.open("frames/steamw%05d.png" % (i,)).resize((640,480))

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
                    if data[x, y][0] > 140: colour =   0b111111
                    elif data[x, y][0] > 80: colour = 0b101010
                    elif data[x, y][0] > 35: colour =  0b010101
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

            #if spans == last_spans:
            #    repeat_count += 1
            #else:
            #    if repeat_count != 0:
            #        out_file.write(struct.pack('>H', 0xf800 + repeat_count))
            #        data_len += 2
            #    repeat_count = 0
            if True:
                if sum([s[0] for s in spans]) != 640:
                    #print(spans)
                    print("Error")
                    sys.exit(0)

                for span in spans:
                    out_file.write(struct.pack('>H', (span[0] << 6) + span[1]))
                data_len += 2 * len(spans)
                #last_spans = spans

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
