import json
import websockets
import asyncio
import os
import aiohttp

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
    self.channels = []
    self.on_channel_added = kwargs.get('on_channel_added')
    self.connected = False
    
  
  async def add_listener(self, msg):
    peerId = msg.get('newListener')

    if (peerId in self.channels):
      return

    print('adding listener', peerId)
    self.send_data({
      type: 'ping',
      message: 'Hello'
    })

    
  async def on_message(self, message):
    msg = json.loads(message)
    event = msg.get('event')

    if event == 'listener_joined':
      print('New Listener Joined', msg.get('newListener'))
      await self.add_listener(msg)


  async def send_data(self, data):
    json_data = json.dumps({
      'data': {
        'data': data,
        'id': self.id,
      },
      'action': 'objectdata'
    })

    print("sending data")
    await self.ws.send(json_data)

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

        if (self.connected):
          return
      except websockets.exceptions.ConnectionClosed:
        print('Websocket connection is closed')
        return
