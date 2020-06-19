from time import sleep, time
import sys
import pyaudio
import wave
import numpy as np
from math import log2, floor, inf
from itertools import chain
from functools import reduce
from random import randint
from .pseudo_audio_client import Client

RATE = 44100
CHANNELS = 1
NP_DTYPE = np.int16
FORMAT = pyaudio.paInt16
CHUNK = 1024

n_freqs = 30 + 1
start = 4000
stop = 8000
step = (stop - start) / (n_freqs - 1)
frequencies = [int(start + step * i) for i in range(n_freqs)]

f_to_l = {f: i for i, f in enumerate(frequencies)}
f_to_l[frequencies[-1]] = -1
duration = 0.1


class Tunnel:
	def __init__(self, typ, addr):
		self.audio_client = Client(typ, addr)

	def up(self):
		pass

	def down(self):
		pass

	def send(self, data):
		data = bytes_to_audio(data, frequencies, duration, RATE)
		data = b''.join(data)
		return self.audio_client.send(data)

	def recv(self):
		data = self.audio_client.recv()
		data = audio_to_bytes(data)
		return data


def load_wav(file):
	wf = wave.open(file, 'rb')
	data = b''
	y = wf.readframes(CHUNK)
	while len(y) != 0:
		data += y
		y = wf.readframes(CHUNK)
	wf.close()
	return data


def to_n_bit_stream(stream, src_n, dst_n):
	quanta = ''
	i = 0
	for data in stream:
		quanta += "{:0{}b}".format(data, src_n)
		while len(quanta) >= dst_n:
			yield int(quanta[:dst_n], 2)
			quanta = quanta[dst_n:]
		i += 1
	if len(quanta) != 0:
		yield int(quanta + '0' * (dst_n - len(quanta)), 2)


def make_sound_quanta(f, duration, fs):
	x = np.sin(2 * np.pi * np.arange(fs * duration + 1) * f / fs)
	y = np.power(
		np.abs(np.sin(np.pi * np.arange(fs * duration + 1) / (fs * duration))), 0.25)
	return (32767 * x * y).astype(NP_DTYPE).tobytes()


def bytes_to_audio(data, frequencies, duration, fs):
	n_levels = len(frequencies) - 1
	bit_size = max(1, floor(log2(n_levels)))
	prev_level = None
	for level in to_n_bit_stream(data, 8, bit_size):
		if level == prev_level:
			yield make_sound_quanta(frequencies[-1], duration, fs)
		yield make_sound_quanta(frequencies[level], duration, fs)
		prev_level = level


def find_frquency(segment):
	w = np.fft.fft(segment)
	freqs = np.fft.fftfreq(len(segment))
	idx = np.argmax(np.abs(w))
	freq = freqs[idx]
	freq_in_hertz = abs(freq * RATE)
	return freq_in_hertz


def fit_to_frequency(f):
	thres = abs(frequencies[1] - frequencies[0]) / 2
	for freq in frequencies:
		if abs(freq - f) <= thres:
			return freq
	return None


def audio_to_bytes(data):
	data = np.frombuffer(data, dtype=NP_DTYPE)

	f_sample_size = int(RATE * duration / 3)
	freqs = [find_frquency(data[i:i + f_sample_size])
          for i in range(0, len(data), f_sample_size)]
	freqs = [fit_to_frequency(f) for f in freqs]
	freqs = filter(lambda f: f is not None, freqs)

	merged_freqs = []
	prev_freq = 0
	for f in freqs:
		if f != prev_freq:
			merged_freqs.append(f)
		prev_freq = f
	freqs = merged_freqs

	data_bytes = [f_to_l[f] for f in freqs]
	data_bytes = filter(lambda b: b != -1, data_bytes)

	n_levels = len(frequencies) - 1
	bit_size = max(1, floor(log2(n_levels)))
	data_bytes = bytes(i for i in to_n_bit_stream(data_bytes, bit_size, 8))

	ret = data_bytes
	return ret


def make_sound(data):
	p = pyaudio.PyAudio()
	stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            output=True
        )
	wf = wave.open("clean-data.wav", 'wb')
	wf.setnchannels(CHANNELS)
	wf.setsampwidth(p.get_sample_size(FORMAT))
	wf.setframerate(RATE)

	for segment in bytes_to_audio(data, frequencies, duration, RATE):
		stream.write(segment)
		wf.writeframes(segment)

	wf.close()
	stream.stop_stream()
	stream.close()
	p.terminate()


def record(file):
	p = pyaudio.PyAudio()
	stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
	wf = wave.open(file, 'wb')
	wf.setnchannels(CHANNELS)
	wf.setsampwidth(p.get_sample_size(FORMAT))
	wf.setframerate(RATE)

	print("RECORDING")
	frames = []
	try:
		while True:
			frames.append(stream.read(CHUNK))
	except:
		pass
	print("DONE")

	wf.writeframes(b''.join(frames))
	wf.close()
	stream.stop_stream()
	stream.close()
	p.terminate()


def test():
	data = load_wav('real-data.wav')
	data = audio_to_bytes(data)
	return data


def its_a_perfect_world():
	og_data = bytes(range(256))

	data = og_data
	print("STARTED ENCODING")
	data = bytes_to_audio(data, frequencies, duration, RATE)
	print("DONE ENCODING")
	data = b''.join(data)
	print("STARTED DECODING")
	data = audio_to_bytes(data)
	print("DONE DECODING")

	assert data == og_data, "Failed"
	print("Success")


if __name__ == "__main__":
	if sys.argv[1] == 'sanity':
		its_a_perfect_world()
	elif sys.argv[1] == 'record':
		record('real-data.wav')
	elif sys.argv[1] == 'play':
		data = b'Hello World!'
		start = time()
		make_sound(data)
		print('%.2f bps' % (8 * len(data) / (time() - start)))
	elif sys.argv[1] == 'test':
		data = b'Hello World!'
		print("Expected:", data)
		op = test()
		print("Received:", op)
		print("Match:", 100 * sum(1 if a == b else 0 for a, b in zip(data, op)) / len(data))
	elif sys.argv[1] == 'ota':
		data = f'{randint(0, 100)} is a number between 0 and 100'.encode()
		t = Tunnel(sys.argv[2], ('localhost', 8080))
		t.up()
		if sys.argv[2] == 'yin':
			t.send(data)
			print("Sent:", data)
		else:
			print("Received:", t.recv())
		t.down()
