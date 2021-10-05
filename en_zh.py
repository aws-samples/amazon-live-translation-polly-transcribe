# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import boto3
import numpy as np
import pyaudio
import wave
import sys
import os
import websocket
import samplerate as sr
import threading
import time
import aiofile
import asyncio

from contextlib import closing
from io import BytesIO
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import Result, Transcript, TranscriptEvent
from pydub import AudioSegment
from pydub.utils import make_chunks
from pydub.playback import play

#Some params
input_rate = 44100
target_rate = 32000
defaultframes = 1024

class textcolors:
    if not os.name == 'nt':
        blue = '\033[94m'
        green = '\033[92m'
        warning = '\033[93m'
        fail = '\033[91m'
        end = '\033[0m'
    else:
        blue = ''
        green = ''
        warning = ''
        fail = ''
        end = ''

recorded_frames = []
device_info = {}
useloopback = False
recordtime = 100

#Use module
p = pyaudio.PyAudio()

#Set default to first in list or ask Windows
try:
    default_device_index = p.get_default_input_device_info()

except IOError:
    default_device_index = -1

#Select Device
print (textcolors.blue + "Available devices:\n" + textcolors.end)

for i in range(0, p.get_device_count()):
    info = p.get_device_info_by_index(i)
    print (textcolors.green + str(info["index"]) + textcolors.end + ": \t %s \n \t %s \n" % (info["name"], p.get_host_api_info_by_index(info["hostApi"])["name"]))
    
    if default_device_index == -1:
        default_device_index = info["index"]

#Handle no devices available
if default_device_index == -1:
    print (textcolors.fail + "No device available. Quitting." + textcolors.end)
    exit()

#Get input or default
device_id = int(input("Choose device [" + textcolors.blue + str(default_device_index) + textcolors.end + "]: ") or default_device_index)
print ("")

#Get device info
try:
    device_info = p.get_device_info_by_index(device_id)

except IOError:
    device_info = p.get_device_info_by_index(default_device_index)
    print (textcolors.warning + "Selection not available, using default." + textcolors.end)

#Choose between loopback or standard mode
is_input = device_info["maxInputChannels"] > 0
is_wasapi = (p.get_host_api_info_by_index(device_info["hostApi"])["name"]).find("WASAPI") != -1

if is_input:
    print (textcolors.blue + "Selection is input using standard mode.\n" + textcolors.end)
else:
    if is_wasapi:
        useloopback = True;
        print (textcolors.green + "Selection is output. Using loopback mode.\n" + textcolors.end)
    else:
        print (textcolors.fail + "Selection is input and does not support loopback mode. Quitting.\n" + textcolors.end)
        exit()

recordtime = int(input("Record time in seconds [" + textcolors.blue + str(recordtime) + textcolors.end + "]: ") or recordtime)
resampler = sr.Resampler()
ratio = target_rate / input_rate

def resample(chunk, target_rate=32000):
    raw_data = chunk
    data = np.fromstring(raw_data, dtype=np.int16)
    resampled_data = resampler.process(data, ratio)

    return resampled_data

#pre-recorded audio file, only for testing
filename = "zoom_test.wav"

polly = boto3.client('polly', region_name = 'us-west-2')
translate = boto3.client(service_name='translate', region_name='us-west-2', use_ssl=True)

transcription = ''

async def mic_stream():
    # This function wraps the raw input stream from the microphone forwarding
    # the blocks to an asyncio.Queue.
    loop = asyncio.get_event_loop()
    input_queue = asyncio.Queue()
    def callback(indata, frame_count, time_info, status):

        loop.call_soon_threadsafe(input_queue.put_nowait, indata)

        return (indata, pyaudio.paContinue)
    # Be sure to use the correct parameters for the audio stream that matches
    # the audio formats described for the source language you'll be using:
    # https://docs.aws.amazon.com/transcribe/latest/dg/streaming.html
    """stream = sounddevice.RawInputStream(
        channels=1,
        samplerate=16000,
        callback=callback,
        blocksize=1024 * 2,
        dtype="int16",
    )
    """
    print(device_info)

    #Open stream
    channelcount = device_info["maxInputChannels"] if (device_info["maxOutputChannels"] < device_info["maxInputChannels"]) else device_info["maxOutputChannels"]
    stream = p.open(format = pyaudio.paInt16,
                channels = channelcount,
                rate = int(device_info["defaultSampleRate"]),
                input = True,
                frames_per_buffer = defaultframes,
                input_device_index = device_info["index"],
                # as_loopback = useloopback,
                stream_callback=callback)
    # Initiate the audio stream and asynchronously yield the audio chunks
    # as they become available.
    stream.start_stream()
    print("started stream")

    while True:
        indata = await input_queue.get()
        yield indata


#below class is from the live streaming transcribe SDK, handles returned streaming transcribe events    
class MyEventHandler(TranscriptResultStreamHandler):
    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        # This handler can be implemented to handle transcriptions as needed.

        results = transcript_event.transcript.results
        print("firing outputs..", results)

        if len(results) > 0:
            if len(results[0].alternatives) > 0:
                transcript = results[0].alternatives[0].transcript

                print("transcript:", transcript)

                print(results[0].channel_id)

                if hasattr(results[0], "is_partial") and results[0].is_partial == False:
                    #translate only 1 channel. the other channel is a duplicate
                    if results[0].channel_id == "ch_0":
                        trans_result = translate.translate_text(
                            Text = transcript,
                            SourceLanguageCode = "en",
                            TargetLanguageCode = "zh"
                        )
                        print("translated text in zh:" + trans_result.get("TranslatedText"))
                        text = trans_result.get("TranslatedText")
                        aws_polly_tts(text)

def stream_data(stream):
    """Consumes a stream in chunks to produce the response's output'"""
    print("Streaming started...")
    chunk = 1024

    # def callback(in_data, frame_count, time_info, status):
    #     data = stream.read(chunk)
    #     return (data, pyaudio.paContinue)

    if stream:

        polly_stream = p.open(
                    format = pyaudio.paInt16,
                    channels = 1,
                    rate = 16000,
                    output = True,
                    # stream_callback=callback
                    )
    # polly_stream.start_stream()

    # while polly_stream.is_active():
    #     time.sleep(0.1)
    
    # polly_stream.stop_stream()
    # polly_stream.close()
        while True:
            data = stream.read(chunk)
            polly_stream.write(data)
            # If there's no more data to read, stop streaming
            if not data:
                stream.close()
                polly_stream.stop_stream()
                polly_stream.close()
                print("got to if not data in stream_data() line 188    :) ")
                break
        print("Streaming completed.")
    else:
        # The stream passed in is empty
        print("Nothing to stream.")


def aws_polly_tts(text):
    response = polly.synthesize_speech(
        Engine = 'standard',
        LanguageCode = 'cmn-CN',
        Text=text,
        VoiceId = "Zhiyu",
        OutputFormat = "pcm",
    )
   
    byte_stream = response['AudioStream']
    stream_data(byte_stream)

    #pyaudio streaming example, open a stream with the right params, read the data in chunks, while data, write the chunk to the open steam, close the stream
    """
    pa = pyaudio.PyAudio()
    op_stream = pa.open(format = pa.get_format_from_width(af.sample_width),
                    channels = af.channels,
                    rate = af.frame_rate,
                    output = True)
    # Read data in chunks
    rd_data = af.(chunk)
    # Play the sound by writing the audio
    # data to the Stream using while loop
    while rd_data != '':
        op_stream.write(rd_data)
        rd_data = af.readframes(chunk)
    # Close and terminate the stream
    op_stream.stop_stream()
    op_stream.close()
    pa.terminate()
    """

async def transcribe():
# Setup up our client with our chosen AWS region
    client = TranscribeStreamingClient(region="us-west-2")
    stream = await client.start_stream_transcription(
        language_code="en-US",
        media_sample_rate_hz=int(device_info["defaultSampleRate"]),
        number_of_channels = 2,
        enable_channel_identification=True,
        media_encoding="pcm",
    )
    recorded_frames = []

    async def write_chunks(stream):
        # This connects the raw audio chunks generator coming from the microphone
        # and passes them salong to the transcription stream.
        print("getting mic stream")
        async for chunk in mic_stream():
            #print("found chunk sending now...")
            #print(len(chunk))
            recorded_frames.append(chunk)
            await stream.input_stream.send_audio_event(audio_chunk=chunk)
        await stream.input_stream.end_stream()
        """
        async with aiofile.AIOFile("zoom_test.wav", 'rb') as afp:
            reader = aiofile.Reader(afp, chunk_size=1024 * 16)
            async for chunk in reader:
                await stream.input_stream.send_audio_event(audio_chunk=chunk)
        await stream.input_stream.end_stream()
        """

    handler = MyEventHandler(stream.output_stream)

    await asyncio.gather(write_chunks(stream), handler.handle_events())

    filename = input("Save as [" + textcolors.blue + "outtesting.wav" + textcolors.end + "]: ") or "outtesting.wav"
    waveFile = wave.open(filename, 'wb')
    waveFile.setnchannels(2)
    waveFile.setsampwidth(p.get_sample_size(pyaudio.paInt16))
    waveFile.setframerate(int(device_info["defaultSampleRate"]))
    waveFile.writeframes(b''.join(recorded_frames))
    waveFile.close()

loop = asyncio.get_event_loop()
loop.run_until_complete(transcribe())
loop.close()

print("done")