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
#import sounddevice
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import Result, Transcript, TranscriptEvent
from pydub import AudioSegment
from pydub.utils import make_chunks
from pydub.playback import play
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
    #print('{} -> {}'.format(len(data), len(resampled_data)))
    return resampled_data
#pre-recorded audio file
filename = "zoom_test.wav"
translate = boto3.client(service_name='translate', region_name='us-west-2', use_ssl=True)
transcription = ''
async def mic_stream():
    # This function wraps the raw input stream from the microphone forwarding
    # the blocks to an asyncio.Queue.
    loop = asyncio.get_event_loop()
    input_queue = asyncio.Queue()
    def callback(indata, frame_count, time_info, status):
        #data = wf.readframes(frame_count)
        #return (data, pyaudio.paContinue)
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
                #rate = 16000,
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
        #indata = resample(stream.read(defaultframes), 32000)
        indata = await input_queue.get()
        #print("sending", indata)
        #print(len(indata))
        yield indata
        #yield resample(indata).tobytes()
class MyEventHandler(TranscriptResultStreamHandler):
    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        #globals transcription
        # This handler can be implemented to handle transcriptions as needed.
        # In this case, we're simply printing the finished 
        results = transcript_event.transcript.results
        print("firing outputs..", results)
        if len(results) > 0:
            if len(results[0].alternatives) > 0:
                transcript = results[0].alternatives[0].transcript
                print(transcript)
                #transcription += transcript
                print("transcript:", transcript)
                #print(dir(results[0]))
                print(results[0].channel_id)
                if hasattr(results[0], "is_partial") and results[0].is_partial == False:
                    #translate only 1 channel. the other channel is a duplicate
                    if results[0].channel_id == "ch_0":
                        trans_result = translate.translate_text(
                            Text = transcript,
                            SourceLanguageCode = "zh",
                            TargetLanguageCode = "en"
                        )
                        print("translated text in en:" + trans_result.get("TranslatedText"))
                        text = trans_result.get("TranslatedText")
                        aws_polly_tts(text)
    # async def handle_transcript_event(self, transcript: Transcript):
    #     # This handler can be implemented to handle transcriptions as needed.
    #     # In this case, we're simply printing the finished 
    #         if transcript.results[0].alternatives[0].is_partial == False:
    #             print(transcript.results[0].alternatives[0].transcript)
polly = boto3.client('polly', region_name = 'us-west-2')
def aws_polly_tts(text):
    response = polly.synthesize_speech(
        Engine = 'standard',
        LanguageCode = 'en-US',
        Text=text,
        VoiceId = "Joanna",
        OutputFormat = "mp3",
    )
    #play back into microphone
    #TODO: playback asap the buffer fills-in
    #https://aws.amazon.com/blogs/machine-learning/building-a-reliable-text-to-speech-service-with-amazon-polly/
    chunk = response['AudioStream'].read()
    #write to a file
    file = open('zh_results_en.mp3','wb')
    file.write(chunk)
    file.close()
    #playback
    chunk = 1024
    # Open a .Stream object to write the WAV file
    # 'output = True' indicates that the
    # sound will be played rather than
    # recorded and opposite can be used for recording
    af = AudioSegment.from_file("zh_results_en.mp3")
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
    play(af)
async def transcribe():
# Setup up our client with our chosen AWS region
    client = TranscribeStreamingClient(region="us-west-2")
    stream = await client.start_stream_transcription(
        language_code="zh-CN",
        #media_sample_rate_hz=16000,
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
    print("1")
    handler = MyEventHandler(stream.output_stream)
    print("2")
    await asyncio.gather(write_chunks(stream), handler.handle_events())
    filename = input("Save as [" + textcolors.blue + "outtesting.wav" + textcolors.end + "]: ") or "outtesting.wav"
    waveFile = wave.open(filename, 'wb')
    waveFile.setnchannels(2)
    waveFile.setsampwidth(p.get_sample_size(pyaudio.paInt16))
    waveFile.setframerate(int(device_info["defaultSampleRate"]))
    waveFile.writeframes(b''.join(recorded_frames))
    waveFile.close()
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