# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/


import boto3
import pyaudio
import wave
import sys
import os
# import websocket
import threading
import time
import aiofile
import asyncio
import sounddevice
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import Result, Transcript, TranscriptEvent
defaultframes = 512


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
p = sounddevice
#Set default to first in list or ask Windows
try:
    default_device_index = p.query_devices(device=0)
except IOError:
    default_device_index = -1
#Select Device
print (textcolors.blue + "Available devices:\n" + textcolors.end)
for i in range(0, len(p.query_devices())):
    info = p.query_devices(device=i)
    #print(info)
    print (textcolors.green + str(i) + textcolors.end + ": \t %s \n \t %s \n" % (info["name"], p.query_hostapis(info["hostapi"])["name"]))
    if default_device_index == -1:
        default_device_index = i
#Handle no devices available
if default_device_index == -1:
    print (textcolors.fail + "No device available. Quitting." + textcolors.end)
    exit()
#Get input or default
device_id = int(input("Choose device [" + textcolors.blue + str(default_device_index) + textcolors.end + "]: ") or default_device_index)
print ("")
#Get device info
try:
    device_info = p.query_devices(device=device_id)
except IOError:
    device_info = p.query_devices(default_device_index)
    print (textcolors.warning + "Selection not available, using default." + textcolors.end)
#Choose between loopback or standard mode
is_input = device_info["max_input_channels"] > 0
print(device_info)
print(p.query_hostapis(device_info["hostapi"]))
is_wasapi = (p.query_hostapis(device_info["hostapi"])["name"]).find("WASAPI") != -1
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
#pre-recorded audio file
print("after input")
filename = "zoom_test.wav"

pa = pyaudio.PyAudio()
translate = boto3.client(service_name='translate', region_name='us-west-2', use_ssl=True)
transcription = ''
async def mic_stream():
    # This function wraps the raw input stream from the microphone forwarding
    # the blocks to an asyncio.Queue.
    loop = asyncio.get_event_loop()
    input_queue = asyncio.Queue()
    def callback(indata, frame_count, time_info, status):
        loop.call_soon_threadsafe(input_queue.put_nowait, (bytes(indata), status))
    # Be sure to use the correct parameters for the audio stream that matches
    # the audio formats described for the source language you'll be using:
    # https://docs.aws.amazon.com/transcribe/latest/dg/streaming.html
    channelcount = device_info["max_input_channels"] if (device_info["max_output_channels"] < device_info["max_input_channels"]) else device_info["max_output_channels"]
    print(channelcount)
    stream = sounddevice.RawInputStream(
        channels=1,
        samplerate=48000,
        callback=callback,
        blocksize=1024 * 2,
        dtype="int16",
        device=device_id
    )
    # Initiate the audio stream and asynchronously yield the audio chunks
    # as they become available.
    with stream:
        while True:
            indata, status = await input_queue.get()
            yield indata, status
class MyEventHandler(TranscriptResultStreamHandler):
    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        #globals transcription
        # This handler can be implemented to handle transcriptions as needed.
        # In this case, we're simply printing the finished 
        results = transcript_event.transcript.results

        for result in results:
            if result.is_partial == False:
                print(result.alternatives[0].transcript)
                transcript = result.alternatives[0].transcript
                print(transcript)
                #transcription += transcript
                print("transcript:", transcript)
                trans_result = translate.translate_text(
                    Text = transcript,
                    SourceLanguageCode = "en",
                    TargetLanguageCode = "zh"
                )
                print("translated text in zh:" + trans_result.get("TranslatedText"))
                text = trans_result.get("TranslatedText")
                aws_polly_tts(text)
    # async def handle_transcript_event(self, transcript: Transcript):
    #     # This handler can be implemented to handle transcriptions as needed.
    #     # In this case, we're simply printing the finished 
    #         if transcript.results[0].alternatives[0].is_partial == False:
    #             print(transcript.results[0].alternatives[0].transcript)
def aws_polly_tts(text):

    chunk = 1024

    polly = boto3.client('polly', region_name = 'us-west-2')
    response = polly.synthesize_speech(
        Engine = 'standard',
        LanguageCode = 'cmn-CN',
        Text=text,
        VoiceId = "Zhiyu",
        OutputFormat = "mp3",
    )




    # Play the sound by writing the audio
    # data to the Stream using while loop

    file = open('response','ab+')
    file.write(response['AudioStream'].read())
    file.close()

    af = wave.open('response', 'rb')
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

async def transcribe():
# Setup up our client with our chosen AWS region
    client = TranscribeStreamingClient(region="us-west-2")
    stream = await client.start_stream_transcription(
        language_code="en-US",
        media_sample_rate_hz=48000,
        # media_sample_rate_hz=16000,
        media_encoding="pcm",
    )
    async def write_chunks(stream):
        # This connects the raw audio chunks generator coming from the microphone
        # and passes them salong to the transcription stream.
        async for chunk, status in mic_stream():
            await stream.input_stream.send_audio_event(audio_chunk=chunk)
        await stream.input_stream.end_stream()
        """
        async with aiofile.AIOFile("zoom_test.wav", 'rb') as afp:
            reader = aiofile.Reader(afp, chunk_size=1024 * 16)
            async for chunk in reader:
                await stream.input_stream.send_audio_event(audio_chunk=chunk)
        await stream.input_stream.end_stream()
        """
    print("1")
    handler = MyEventHandler(stream.output_stream)
    print("2")
    await asyncio.gather(write_chunks(stream), handler.handle_events())
    print("3")
loop = asyncio.get_event_loop()
loop.run_until_complete(transcribe())
loop.close()
# async def main():
#     # Instantiate our handler and start processing events
#     loop = asyncio.get_event_loop()
#     print("did the thing")
#     return
# if __name__ == "__main__":
#     asyncio.run(main())
#     # main()
print("done")