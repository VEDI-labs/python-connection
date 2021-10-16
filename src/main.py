# 
from threading import Thread
from resilient import ResilientObject
from dotenv import load_dotenv
import asyncio
import os
import jwt
from random import randint

load_dotenv()
# Variables loaded from environment file
NONCE = os.getenv('NONCE')
DEVICE_ID = os.getenv('DEVICE_ID')
SERVER_URL = os.getenv('SERVER_URL')
TOKEN_URL = os.getenv('TOKEN_URL')

resilient_object = None
stop = False
channels = []

def generate_token():
  # Read secret key
  secret_file = open('./src/master.key', 'r')
  SECRET=secret_file.read()
  headers = {
    'kid': DEVICE_ID,
    'alg': 'RS256'
  }

  payload = {
    'nonce': NONCE
  }

  return jwt.encode(payload, SECRET, algorithm='RS256', headers=headers)

def connect_object(loop):
  try:
    global resilient_object
    asyncio.set_event_loop(loop)
    jwt_token = generate_token()
    # Create Token
    device_token = loop.run_until_complete(ResilientObject.get_device_token(TOKEN_URL, token=jwt_token))

    # Create connection
    connection = loop.run_until_complete(ResilientObject.create(SERVER_URL, token=device_token))
    # Connect object and make it available on plattform
    resilient_object = ResilientObject(connection, id=DEVICE_ID, name="Python Object")
    loop.run_until_complete(resilient_object.connect())

    # Listen for events
    loop.run_until_complete(resilient_object.listen())
    loop.run_forever()
  except Exception as e:
    pass

async def send_data():
  ### Aca ejecutamos la funcion principal
  global stop
  while not stop:
    await asyncio.sleep(5)
    i = randint(0, 100)
    if (resilient_object):
      await resilient_object.send_data({
        'message': 'Mensaje',
        'value': i
      })
      i = i + 1

try:
  loop = asyncio.new_event_loop()
  thread = Thread(target=connect_object, args=(loop,),)
  thread.start()

  asyncio.run(send_data())
except KeyboardInterrupt:
  stop = True
  print('bye')
  exit()


