#!/usr/bin/env python

# Copyright 2017 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Google Cloud Speech API sample that demonstrates word time offsets.

Example usage:
    python transcribe_word_time_offsets.py resources/audio.raw
    python transcribe_word_time_offsets.py \
        gs://cloud-samples-tests/speech/vr.flac
"""

import argparse
import io

import pyaudio
import wave

session = {'time':0.0, 'count':0}

class SpeechRec(object):

    def __init__(self, speech_file):
        self.transcribe_file_with_word_time_offsets(speech_file)

    def transcribe_file_with_word_time_offsets(self, speech_file):
        """Transcribe the given audio file synchronously and output the word time
        offsets."""
        from google.cloud import speech
        from google.cloud.speech import enums
        from google.cloud.speech import types
        client = speech.SpeechClient()

        with io.open(speech_file, 'rb') as audio_file:
            content = audio_file.read()

        audio = types.RecognitionAudio(content=content)
        config = types.RecognitionConfig(
            encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code='en-US',
            enable_word_time_offsets=True)

        response = client.recognize(config, audio)

        for result in response.results:
            alternative = result.alternatives[0]
            print('Transcript: {}'.format(alternative.transcript))

            # for word_info in alternative.words:
            #     word = word_info.word
            #     start_time = word_info.start_time
            #     end_time = word_info.end_time
            #     print('Word: {}, start_time: {}, end_time: {}'.format(
            #         word,
            #         start_time.seconds + start_time.nanos * 1e-9,
            #         end_time.seconds + end_time.nanos * 1e-9))
            start_time = alternative.words[0].start_time
            start = start_time.seconds + start_time.nanos * 1e-9
            end_time = alternative.words[len(alternative.words)-1].start_time
            end = end_time.seconds + end_time.nanos * 1e-9
            # PRINT
            # print("Word count: {} Time used: ".format(len(alternative.words)), (end-start))
            # print("Word Per Min: {}".format(len(alternative.words)/((end-start)/60)))
            # save this to array
            session['time'] += (end-start)
            session['count'] += len(alternative.words)

    # [START def_transcribe_gcs]
    # def transcribe_gcs_with_word_time_offsets(gcs_uri):
    #     """Transcribe the given audio file asynchronously and output the word time
    #     offsets."""
    #     from google.cloud import speech
    #     from google.cloud.speech import enums
    #     from google.cloud.speech import types
    #     client = speech.SpeechClient()

    #     audio = types.RecognitionAudio(uri=gcs_uri)
    #     config = types.RecognitionConfig(
    #         encoding=enums.RecognitionConfig.AudioEncoding.FLAC,
    #         sample_rate_hertz=16000,
    #         language_code='en-US',
    #         enable_word_time_offsets=True)

    #     operation = client.long_running_recognize(config, audio)

    #     print('Waiting for operation to complete...')
    #     result = operation.result(timeout=90)

    #     for result in result.results:
    #         alternative = result.alternatives[0]
    #         print('Transcript: {}'.format(alternative.transcript))
    #         print('Confidence: {}'.format(alternative.confidence))

    #         for word_info in alternative.words:
    #             word = word_info.word
    #             start_time = word_info.start_time
    #             end_time = word_info.end_time
    #             print('Word: {}, start_time: {}, end_time: {}'.format(
    #                 word,
    #                 start_time.seconds + start_time.nanos * 1e-9,
    #                 end_time.seconds + end_time.nanos * 1e-9))

    # [END def_transcribe_gcs]

class Recorder(object):
    '''A recorder class for recording audio to a WAV file.
    Records in mono by default.
    '''

    def __init__(self, channels=1, rate=16000, frames_per_buffer=1024):
        self.channels = channels
        self.rate = rate
        self.frames_per_buffer = frames_per_buffer

    def open(self, fname, mode='wb'):
        return RecordingFile(fname, mode, self.channels, self.rate,
                            self.frames_per_buffer)

class RecordingFile(object):
    def __init__(self, fname, mode, channels, 
                rate, frames_per_buffer):
        self.fname = fname
        self.mode = mode
        self.channels = channels
        self.rate = rate
        self.frames_per_buffer = frames_per_buffer
        self._pa = pyaudio.PyAudio()
        self.wavefile = self._prepare_file(self.fname, self.mode)
        self._stream = None

    def __enter__(self):
        return self

    def __exit__(self, exception, value, traceback):
        self.close()

    def record(self, duration):
        # Use a stream with no callback function in blocking mode
        self._stream = self._pa.open(format=pyaudio.paInt16,
                                        channels=self.channels,
                                        rate=self.rate,
                                        input=True,
                                        frames_per_buffer=self.frames_per_buffer)
        for _ in range(int(self.rate / self.frames_per_buffer * duration)):
            audio = self._stream.read(self.frames_per_buffer)
            self.wavefile.writeframes(audio)
        return None

    def start_recording(self):
        # Use a stream with a callback in non-blocking mode
        self._stream = self._pa.open(format=pyaudio.paInt16,
                                        channels=self.channels,
                                        rate=self.rate,
                                        input=True,
                                        frames_per_buffer=self.frames_per_buffer,
                                        stream_callback=self.get_callback())
        self._stream.start_stream()
        return self

    def stop_recording(self):
        self._stream.stop_stream()
        return self

    def get_callback(self):
        def callback(in_data, frame_count, time_info, status):
            self.wavefile.writeframes(in_data)
            return in_data, pyaudio.paContinue
        return callback


    def close(self):
        self._stream.close()
        self._pa.terminate()
        self.wavefile.close()

    def _prepare_file(self, fname, mode='wb'):
        wavefile = wave.open(fname, mode)
        wavefile.setnchannels(self.channels)
        wavefile.setsampwidth(self._pa.get_sample_size(pyaudio.paInt16))
        wavefile.setframerate(self.rate)
        return wavefile

if __name__ == '__main__':

    filename = "file.raw"

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        'path', help='File or GCS path for audio file to be recognized')
    args = parser.parse_args()
    # if args.path.startswith('gs://'):
    #     transcribe_gcs_with_word_time_offsets(args.path)
    # else:
    #     transcribe_file_with_word_time_offsets(args.path)


    # record audio
    subject = 0
    hasStarted = False
    print("record audio: input 0 for start and 1 for stop")
    while (1):
        x = input()
        if (x == 0):
            hasStarted = True
            # subject += 1
            # filename = "file{}.raw".format(subject)
            recorder = Recorder()
            recording_file = recorder.open(filename)
            recording_file.start_recording()
        if (x == 1):
            if hasStarted == False:
                break;
            else:
                hasStarted = False
            recording_file.stop_recording()
            recording_file.close()
            # processing speech
            SpeechRec(args.path)
            # transcribe_gcs_with_word_time_offsets(args.path)
            # compute
            minutes = session['time']/60
            count = session['count']
            print("************ Total Words Per Min ************")
            print(count/minutes)
        if (x == 3):
            print("terminate")
            break;




