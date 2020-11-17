'''
Decoder for FrSky F.PORT protocol
Does *not* handle uplink frames. If uplink frames are present the decoder will probably get confused
'''

from .pd import Decoder
