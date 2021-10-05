# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/



import pydub
import os
from pathlib import Path
from pydub.playback import play
from pydub import AudioSegment

my_file = Path("D:\\Users\\cameron\\Desktop\\zoom_s2s\\zoom_bot\\response.mp3")

pydub.AudioSegment.converter = os.getcwd()+ "\\ffmpeg.exe"                    
pydub.AudioSegment.ffprobe   = os.getcwd()+ "\\ffprobe.exe"
sound = pydub.AudioSegment.from_mp3(os.getcwd()+"\\response.mp3")

 
# something = AudioSegment.from_file('D:\\Users\\cameron\\Desktop\\zoom_s2s\\zoom_bot\\response.mp3')

play(sound)