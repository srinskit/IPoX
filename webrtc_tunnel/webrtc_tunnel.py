from time import sleep
from threading import Thread
import random
import argparse
import asyncio
import queue

from aiortc import RTCIceCandidate, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.signaling import BYE, ApprtcSignaling


class WebRTCTunnel:
	def __init__(self, room):
		self.channel = None
		self.recv_q = queue.Queue()
		self.send_q = queue.Queue()
		self.room = "".join([random.choice("0123456789")
                       for x in range(10)]) if room is None else room

		self.webrtc_thread = Thread(target=self.webrtc_handler)

	def send(self, data):
		return self.send_q.put(data)

	def recv(self):
		return self.recv_q.get()

	def up(self):
		self.webrtc_thread.start()

	def down(self):
		self.send(0)
		self.webrtc_thread.join()

	async def consume_signaling(self, pc, signaling):
		while True:
			obj = await signaling.receive()

			if isinstance(obj, RTCSessionDescription):
				await pc.setRemoteDescription(obj)

				if obj.type == "offer":
					await pc.setLocalDescription(await pc.createAnswer())
					await signaling.send(pc.localDescription)
			elif isinstance(obj, RTCIceCandidate):
				await pc.addIceCandidate(obj)
			elif obj is BYE:
				print("Got exit signal")
				self.send(0)
				break

	async def consume_send_q(self, signaling):
		running = True
		while running:
			# Note seperate empty check and get used as there is only one consumer
			while not self.send_q.empty():
				data = self.send_q.get()
				if data == 0:
					running = False
					self.recv_q.put(None)
					await signaling.send(BYE)
				elif self.channel is not None:
					if len(data) == 52:
						# BUG: Router Solicitation message eventually
						# breaks the P2P connection
						continue
					self.channel.send(data)
			await asyncio.sleep(.1)

	async def run(self, pc, signaling):
		params = await signaling.connect()

		if params["is_initiator"] == "true":
			channel = pc.createDataChannel("chat")
			print("Data channel created")

			@channel.on("open")
			def on_open():
				self.channel = channel

			@channel.on("message")
			def on_message(data):
				self.recv_q.put(data)

			# send offer
			await pc.setLocalDescription(await pc.createOffer())
			await signaling.send(pc.localDescription)

		else:
			@pc.on("datachannel")
			def on_datachannel(channel):
				print("Joined channel")
				self.channel = channel

				@channel.on("message")
				def on_message(message):
					self.recv_q.put(message)

		task1 = asyncio.create_task(self.consume_signaling(pc, signaling))
		task2 = asyncio.create_task(self.consume_send_q(signaling))
		await task1
		await task2

	def webrtc_handler(self):
		signaling = ApprtcSignaling(self.room)
		pc = RTCPeerConnection()
		loop = asyncio.new_event_loop()
		try:
			loop.run_until_complete(self.run(pc, signaling))
		except KeyboardInterrupt:
			pass
		finally:
			loop.run_until_complete(pc.close())
			loop.run_until_complete(signaling.close())


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("room", nargs="?")

	args = parser.parse_args()

	tunnel = WebRTCTunnel(args.room)
	running = True

	def send_loop():
		while running:
			tunnel.send(b"PING")
			sleep(1)

	def recv_loop():
		while running:
			data = tunnel.recv()
			if data is not None:
				print(data)
				sleep(1)

	tunnel.up()
	try:
		t1 = Thread(target=send_loop)
		t2 = Thread(target=recv_loop)
		t1.start()
		t2.start()
		input()
	except KeyboardInterrupt:
		pass
	finally:
		running = False
		t1.join()
		t2.join()
		tunnel.down()
