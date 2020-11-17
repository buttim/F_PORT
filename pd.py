import sigrokdecode as srd
import math
from common.srdhelper import SrdIntEnum

class Decoder(srd.Decoder):
    api_version = 3
    id = 'F_PORT'
    name = "F_PORT"
    longname = "FrSky F.PORT"
    desc = 'FrSky F.PORT.'
    license = 'lgplv2+'
    inputs = ['uart']
    outputs = []
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
        ('channeldata','Channel data'),
        ('prim','prim'),
        ('appid','App.ID'),
        ('data','Data'),
    )
    annotation_rows = (
        ('frm', 'Framing', (0,1,2,3,4,5,6,7,)),
        ('chdata', 'Channel data', (8,9,10,11)),
    )
    binary = (
    )

    def __init__(self):
        self.reset()
        
    def reset(self):
        self.insync=False
        self.inframe=False
        self.ss=0
        self.nbyte=0
        self.stuffing=False
        self.length=0
        self.sum=0
        self.type=0
        self.lastss=0
        self.payload=[]
        self.channelss=0
        self.nbit=0
        self.chanvalue=0
        self.appid=0
        self.data=0

    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)

    def metadata(self, key, value):
        if key == srd.SRD_CONF_SAMPLERATE:
            if value!=115200:
                print("warning! wrong baudrate: "+str(value),flush=True)
        
    def decode(self, ss, es, data):
        if data[0] == 'FRAME':
            byte=data[2][0]
            if not self.insync:
                if byte==0x7E:
                    self.insync=True
                else:
                    return
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
                        if self.nbyte==0:       #just synced maybe? (not tested!)
                            self.put(self.lastss, es, self.out_ann, [0, ['HEAD','H']])
                            self.inframe=True
                            self.nbyte=0
                            self.sum=0
                            return
                        self.inframe=False
                        self.payload=[]
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
                        self.payload.append(byte)
                        self.nbyte=self.nbyte+1
                        if self.nbyte==self.length+1:
                            if self.type==0:
                                self.put(self.ss, es, self.out_ann, [3, ['CHANNEL DATA','CHANNELS','CHAN','C']])
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
        elif data[0]=='DATA':
            if self.type==0:
                #print(data[2],flush=True)
                bits=data[2][1]
                if self.nbyte==24:
                    ch17=bits[0][0]
                    ch18=bits[1][0]
                    framelost=bits[2][0]
                    failsafe=bits[3][0]
                    flags='CH17:'+str(ch17)+' CH18:'+str(ch18)+\
                        ' FRAMELOST:'+str(framelost)+' FAILSAFE:'+str(failsafe)
                    self.put(bits[0][1], bits[7][2], self.out_ann, [8, \
                        ['FLAGS',flags]])
                elif self.nbyte==25:
                    self.put(bits[0][1], bits[7][2], self.out_ann, [8, ['RSSI','RSSI: '+str(data[2][0])]])
                elif self.nbyte==2:
                    self.nbit=0
                if self.nbyte>=2 and self.nbyte<24:
                    for i in range(8):
                        if math.floor(self.nbit/11)<16:
                            if self.nbit%11==0:
                                self.channelss=bits[i][1]
                                self.chanvalue=0
                            self.chanvalue=self.chanvalue+bits[i][0]*2**(self.nbit%11)
                            if self.nbit%11==10:
                                label='CH'+str(1+math.floor(self.nbit/11))
                                self.put(self.channelss, bits[i][2], self.out_ann, [8, \
                                    [label,label+': '+str(self.chanvalue)]])
                        self.nbit=self.nbit+1
            elif self.type==1:
                if self.nbyte==2:
                    self.put(ss, es, self.out_ann, [9, ['PRIM','P']])
                elif self.nbyte==3:
                    self.channelss=ss
                    self.appid=data[2][0]
                elif self.nbyte==4:
                    self.appid=self.appid+256*data[2][0]
                    self.put(self.channelss, es, self.out_ann, [10, ['APPID: '+hex(self.appid),'APPID','A']])
                elif self.nbyte>4 and self.nbyte<=8:
                    self.data=self.data+data[2][0]*256**(self.nbyte-5)
                    if self.nbyte==5:
                        self.channelss=ss
                    if self.nbyte==8:
                        self.put(self.channelss, es, self.out_ann, [10, ['DATA: '+str(self.data),'DATA','D']])
