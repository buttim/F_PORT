import sigrokdecode as srd
from common.srdhelper import SrdIntEnum

class Decoder(srd.Decoder):
    api_version = 3
    id = 'F_PORT'
    name = "F_PORT"
    longname = "FrSky F.PORT"
    desc = 'FrSky F.PORT.'
    license = 'gplv2+'
    inputs = ['uart']
    outputs = ['F_PORT']
    tags = ['RC']
    channels = (
    )
    optional_channels = (
    )
    options = (
    )    
    annotations = (
        ('head', 'Frame header'),
        ('len', 'Frame length'),
        ('type', 'Frame type'),
        ('channels', 'Channels Data'),
        ('checksum','Checksum'),
        ('end','Frame end'),
        ('downlink','Downlink'),
        ('uplink','Uplink'),
    )
    annotation_rows = (
        ('data', 'data', (0,1,2,3,4,5,6,7)),
    )
    binary = (
    )

    def __init__(self):
        self.reset()
        
    def reset(self):
        self.inframe=False
        self.ss=0
        self.nbyte=0
        self.stuffing=False
        self.length=0
        self.sum=0
        self.type=0
        self.lastss=0

    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)

    def metadata(self, key, value):
        if key == srd.SRD_CONF_SAMPLERATE:
            if value!=115200:
                print("warning! wrong baudrate: "+str(value),flush=True)
        
    def decode(self, ss, es, data):
        if data[0] == 'FRAME':
            byte=data[2][0]
            if self.stuffing:
                if byte==0x5D:
                    byte=0x7D
                elif byte==0x5E:
                    byte=0x7E
            else:
                self.lastss=ss

            if (not self.stuffing) and byte==0x7D:
                self.stuffing=True
            else:
                self.sum=self.sum+byte
                if self.inframe:
                    if not self.stuffing and byte==0x7E:
                        self.inframe=False
                        if self.nbyte!=self.length+2:
                            ##CHECK
                            self.put(self.lastss, es, self.out_ann, [0, ['BAD FRAME '+str(self.nbyte)+'+'+str(self.length),'BF']])
                        else:
                            self.put(self.lastss, es, self.out_ann, [5, ['END','E']])
                    elif self.nbyte==0:
                        self.put(self.lastss, es, self.out_ann, [1, ['LENGTH','L']])
                        self.length=byte
                        self.nbyte=1
                    elif self.nbyte==1:
                        self.put(self.lastss, es, self.out_ann, [2, ['TYPE','T']])
                        self.type=byte
                        self.nbyte=2
                    else:
                        if self.nbyte==2:
                            self.ss=ss
                        self.nbyte=self.nbyte+1
                        if self.nbyte==self.length+1:
                            if self.type==0:
                                self.put(self.ss, es, self.out_ann, [3, ['CHANNELS','C']])
                            elif self.type==1:
                                self.put(self.ss, es, self.out_ann, [6, ['DOWNLINK','D']])
                            elif self.type==0x81:   #NOT TESTED
                                self.put(self.ss, es, self.out_ann, [7, ['UPLINK','U']])
                        if self.nbyte==self.length+2:
                            while self.sum>0xFF:
                                self.sum=(self.sum>>8)+(self.sum&0xFF)
                            if self.sum==0xFF:
                                self.put(self.lastss, es, self.out_ann, [4, ['CHECKSUM','K']])
                            else:
                                self.put(self.lastss, es, self.out_ann, [4, ['BAD CHECKSUM','BK']])
                                print(hex(self.sum),flush=True);
                else:
                    if (not self.stuffing) and byte==0x7E:
                        self.put(self.lastss, es, self.out_ann, [0, ['HEAD','H']])
                        self.inframe=True
                        self.nbyte=0
                        self.sum=0
                self.stuffing=False
