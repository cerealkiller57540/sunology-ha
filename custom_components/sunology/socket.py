""" Sunology socket-io implementation """
import logging

import asyncio
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed
from homeassistant.exceptions import HomeAssistantError

import json
from .const import PACKAGE_NAME

_LOGGER = logging.getLogger(f"{PACKAGE_NAME}-socket")
class SunologySocket():
    """docstring for SunologySocket"""
    def __init__(self):
        self._on_productInfo_callback = None
        self._on_solarEvent_callback = None
        self._on_batteryEvent_callback = None
        self._on_gridEvent_callback = None
        self._on_onOffEvent_callback = None
        self._on_connect_callback = None
        self._on_disconnect_callback = None
        self._socket = None
        self._connected = False


    def subscribe_on_productInfo(self, callback_function):
        """event: tells you authentication informations."""
        self._on_productInfo_callback = callback_function

    def subscribe_on_solarEvent(self, callback_function):
        """event: tells you authentication informations."""
        self._on_solarEvent_callback = callback_function
    
    def subscribe_on_onOffEvent(self, callback_function):
        """event: tells you authentication informations."""
        self._on_onOffEvent_callback = callback_function

    def subscribe_on_batteryEvent(self, callback_function):
        """event: tells you when a device is added to the gateway."""
        self._on_batteryEvent_callback = callback_function

    def subscribe_on_gridEvent(self, callback_function):
        """event: tells you when a device trigger an alarm."""
        self._on_gridEvent_callback = callback_function
    
    def subscribe_on_connect(self, callback_function):
        """event: tells you when you are connected to the socket."""
        self._on_connect_callback = callback_function
    
    def subscribe_on_disconnect(self, callback_function):
        """event: tells you when you have lost connection of the socket."""
        self._on_disconnect_callback = callback_function

    def _execute_callback_function_safe(self, function_name, function, data):
        """ execute_function """
        if function is not None:
            _LOGGER.debug('Execute function %s with data %s', function_name, json.dumps(data))
            try:
                function(data)
            except HomeAssistantError:
                pass
            except Exception as e:
                _LOGGER.exception('Error while executing function %s:', function_name)
        else:
            _LOGGER.debug('No function to execute for %s', function_name)

    def on_productInfo(self, data):
        """ on_productInfo """
        _LOGGER.debug('ProductInfo received: %s', data)
        self._execute_callback_function_safe('on_productInfo', self._on_productInfo_callback, data)
    
    def on_solarEvent(self, data):
        """ on_solarEvent """
        _LOGGER.debug('SolarEvent received: %s', data)
        self._execute_callback_function_safe('on_solarEvent', self._on_solarEvent_callback, data)
    
    def on_onOffEvent(self, data):
        """ on_solarEvent """
        _LOGGER.debug('OnOffEvent received: %s', data)
        self._execute_callback_function_safe('on_onOffEvent', self._on_onOffEvent_callback, data)
    
    def on_batteryEvent(self, data):
        """ on_batteryEvent """
        _LOGGER.debug('Battery event received: %s', data)
        self._execute_callback_function_safe('on_batteryEvent', self._on_batteryEvent_callback, data)
    
    def on_gridEvent(self, data):
        """ on_gridEvent """
        _LOGGER.debug('Grid event received: %s', data)
        self._execute_callback_function_safe('on_gridEvent', self._on_gridEvent_callback, data)
    
    def on_connect(self):
        """ event: connected """
        _LOGGER.info('Sunology socket connected')
        if self._on_connect_callback is not None:
            self._on_connect_callback()

    @property
    def is_connected(self):
        return self._connected

    def on_disconnect(self):
        """ event: disconnected """
        _LOGGER.warning('Sunology socket disconnected')
        if self._on_disconnect_callback is not None:
            self._on_disconnect_callback()

    def process(self, raw_message):
        """ process the received messages """
        try:
            message = json.loads(raw_message)
            if 'event' in message:
                match message['event']:
                    case "productInfo":
                        self.on_productInfo(message['data'])
                    case "solarEvent":
                        self.on_solarEvent(message['data'])
                    case "batteryEvent":
                        self.on_batteryEvent(message['data'])
                    case "gridEvent":
                        self.on_gridEvent(message['data'])
                    case "onOffEvent":
                        self.on_onOffEvent(message['data'])
                    case "justPaired":
                        # Sent once when an accessory joins; data is its productInfo
                        # (fw-sconnect JSON_TOOLS_getLan_DeviceJustPairedContent).
                        self.on_productInfo(message['data'])
                    case _:
                        _LOGGER.warning('Unmanaged event received: %s', message['event'])
            else:
                _LOGGER.warning('Invalid event received: %s', message)
        except json.JSONDecodeError as err :
            _LOGGER.warning(f"Non json event received: {message}, {err=}, {type(err)=}")
        except UnicodeDecodeError as err :
            _LOGGER.warning(f"Non json event received: {message}, {err=}, {type(err)=}")

    async def send_hub_command(self, body):
        """ send a command to the hub """
        if self._connected:
            await self._socket.send(json.dumps({"event": "hubCommand", "data": body}))
        else:
            _LOGGER.warning('Socket not connected')

    async def connect(self, lan_host_ip, lan_port, auth_token, basepath="ws", end_timeout=5):
        """ connect to the sunology socket"""
        _LOGGER.info('Socket connection call %s', lan_host_ip)
        if self._connected:
            _LOGGER.warning('Socket already connected')
            return

        _LOGGER.debug('Socket not connected')

        try:
            # end_timeout only bounds the handshake. It must never wrap the receive
            # loop below: asyncio.timeout is a deadline on its whole block, so a
            # healthy connection would be torn down after end_timeout seconds.
            async with asyncio.timeout(end_timeout):
                if auth_token is not None:
                    _LOGGER.info('Auth connection')
                    websocket = await connect(
                        f"ws://{lan_host_ip}:{lan_port}/{basepath}",
                        open_timeout=10,
                        ping_timeout=20,
                        ping_interval=20,
                        close_timeout=10,
                        additional_headers={'token': auth_token}
                    )
                else:
                    _LOGGER.info('Unauth connection')
                    websocket = await connect(
                        f"ws://{lan_host_ip}:{lan_port}/{basepath}",
                        open_timeout=10,
                        ping_timeout=20,
                        ping_interval=20,
                        close_timeout=10
                    )

            self._socket = websocket
            self._connected = True
            self.on_connect()

            # Lost links are detected by the websockets keepalive (ping_interval /
            # ping_timeout), which closes the connection and ends this iteration.
            try:
                async for message in self._socket:
                    self.process(message)
            except ConnectionClosed:
                _LOGGER.info("Connection closed by server")
            except asyncio.TimeoutError:
                _LOGGER.warning("Message receive timeout")
            except Exception as e:
                _LOGGER.warning(f"Error receiving message: {e}")

        except asyncio.TimeoutError:
            _LOGGER.warning("Handshake timeout - server unreachable")
        except ConnectionClosed:
            _LOGGER.info("Connection closed during setup")
        except Exception as e:
            _LOGGER.warning(f"Connection error: {e}")
        finally:
            self._connected = False
            if self._socket is not None:
                try:
                    await self._socket.close()
                except:
                    pass
            self.on_disconnect()

        
    async def disconnect(self):
        """Disconnect from the sunology socket"""
        self._connected = False
        if self._socket is not None:
            try:
                await self._socket.close()
            except Exception:
                _LOGGER.debug("Error closing socket", exc_info=True)
        # No on_disconnect() here: closing the socket ends the receive loop of
        # connect(), whose finally block reports the disconnection exactly once.
