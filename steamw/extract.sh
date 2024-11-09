#!/bin/bash
mkdir frames
ffmpeg -i Steamboat_Willie_\(1928\)_by_Walt_Disney.webm -r 60 "frames/steamw%05d.png"
ffmpeg -i Steamboat_Willie_\(1928\)_by_Walt_Disney.webm -ar 30000 -acodec pcm_u8 -ac 1 steamw.wav
