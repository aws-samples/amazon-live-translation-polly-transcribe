# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/



import boto3
import pyaudio
import wave
import sys
import os
import websocket
try:
    import thread
except ImportError:
    import _thread as thread
import time

#wave test filename
filename = "zoom_test.wav"
# Set chunk size of 1024 samples per data frame
chunk = 1024
pa = pyaudio.PyAudio()

# Open the soaudio/sound file
af = wave.open(filename, 'rb')



def get_audio():
    # Create an interface to PortAudio


    # Open a .Stream object to write the WAV file
    # 'output = True' indicates that the
    # sound will be played rather than
    # recorded and opposite can be used for recording
    stream = pa.open(format = pa.get_format_from_width(af.getsampwidth()),
                    channels = af.getnchannels(),
                    rate = af.getframerate(),
                    output = True)

    # Read data in chunks
    rd_data = af.readframes(chunk)

    # Play the sound by writing the audio
    # data to the Stream using while loop


    while len(rd_data) > 0:

        stream.write(rd_data)
        rd_data = af.readframes(chunk)
        print(rd_data)


    print("make it here?")

    # Close and terminate the stream
    stream.stop_stream()
    stream.close()
    pa.terminate()

    return "success"


get_audio()



# def main():
#     print(get_audio())
#     print("did the thing")

#     return

# if __name__ == "__main__":
#     main()

# print("done")


