import json
import websockets
import asyncio
import os
import aiohttp

from aiortc import RTCIceCandidate, RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer
from aiortc.sdp import candidate_from_sdp

class ResilientObject(object):
  @staticmethod
  async def get_device_token(uri, **kwargs):
    authorization_header = kwargs.get('token').decode('utf-8')
    print('generating new token')
    async with aiohttp.ClientSession() as session:
      async with session.post(uri, data=None, headers={'Authorization': authorization_header}) as response:
        body = await response.text()
        return json.loads(body)

  @staticmethod
  async def create(uri, **kwargs):
    authorization_header = str(kwargs.get('token'))
    ws = await websockets.connect(uri, extra_headers = {
      'Authorization': authorization_header
    })

    print('connected to server')
    return ws

  def __init__(self, ws, **kwargs):   
    # Assign attributes that we'll use later
    self.endpoint = kwargs.get('uri', '')
    self.name = kwargs['name']
    self.id = kwargs['id']
    self.ws = ws
    self.listeners = {}
    self.channels = []
    self.on_channel_added=kwargs.get('on_channel_added')
    
  
  async def add_listener(self, msg):
    peerId = msg.get('newListener')

    if (peerId in self.listeners.keys()):
      return

    server = RTCIceServer(urls='stun:stun.1.google.com:19302')
    config = RTCConfiguration([server])
    pc = RTCPeerConnection(configuration=config)
    self.listeners[peerId] = pc


  async def on_session_description(self, msg):
    peerId = msg.get('peerId')
    peer = self.listeners[peerId]
    if (not peer):
      return
    
    args = msg.get('sessionDescription')
    description = RTCSessionDescription(**args)
    await peer.setRemoteDescription(description)

    @peer.on('datachannel')
    def on_datachannel(channel):
      self.channels.append(channel)

      @channel.on('message')
      def on_message(message):
        print(message)
        channel.send('pong')

    if (args['type'] == 'offer'):
      ## set up local description and send answer
      answer = await peer.createAnswer()
      await peer.setLocalDescription(answer)

      local_description = peer.localDescription
      data = {
        "action": "objectsession",
        "data": {
          "id": self.id,
          "peerId": peerId,
          "sessionDescription": {
            "sdp": local_description.sdp,
            "type": local_description.type
          }
        },
      }

      dumped_data = json.dumps(data)
      await self.ws.send(dumped_data)

  async def add_ice_candidate(self, msg):
    peerId = msg.get('peerId')
    peer = self.listeners[peerId]

    args = msg.get('iceCandidate')
    candidate = candidate_from_sdp(args['candidate'])

    candidate.sdpMid = args['sdpMid']
    candidate.sdpMLineIndex = args['sdpMLineIndex']
    
    await peer.addIceCandidate(candidate)
    
  async def on_message(self, message):
    msg = json.loads(message)
    event = msg.get('event')

    if event == 'listener_joined':
      print('New Listener Joined', msg.get('newListener'))
      await self.add_listener(msg)

    if (event == 'session_description'):
      print('setting up remote session description')
      await self.on_session_description(msg)
    
    if (event == 'ice_candidate'):
      print('adding ice candidate')
      await self.add_ice_candidate(msg)
    return

  def send_data(self, data):   
    for channel in self.channels:
      print('sending', data)
      channel.send(str(data))

  async def connect(self, callback=None):
    data = {
      "action": "connectobject",
      "data": {
        "id": self.id,
        "name": self.name
      }
    }

    dumped_data = json.dumps(data)
    await self.ws.send(dumped_data)
    print("connected as ", self.id)


  async def listen(self):
    while self.ws.open:
      try:
        data = await self.ws.recv()
        await self.on_message(data)
      except websockets.exceptions.ConnectionClosed:
        print('Websocket connection is closed')
        return
