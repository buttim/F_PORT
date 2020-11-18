'''
Decoder for FrSky F.PORT protocol.
Two way UART on a single wire
Used by FrSky  RC receivers to send channel data and receive telemetry from sensors
Documentation
https://github.com/betaflight/betaflight/files/1491056/F.Port.protocol.betaFlight.V2.1.2017.11.21.pdf
'''

from .pd import Decoder
