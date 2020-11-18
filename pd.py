import sigrokdecode as srd
import math


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
        ('checksum', 'Checksum'),
        ('end', 'Frame end'),
        ('downlink', 'Downlink'),
        ('uplink', 'Uplink'),
        ('channeldata', 'Channel data'),
        ('prim', 'prim'),
        ('appid', 'App.ID'),
        ('data', 'Data'),
    )
    annotation_rows = (
        ('frm', 'Framing', (0, 1, 2, 3, 4, 5, 6, 7, )),
        ('chdata', 'Channel data', (8, 9, 10, 11)),
    )
    binary = (
    )

    def __init__(self):
        self.reset()

    def reset(self):
        self.insync = False
        self.inframe = False
        self.ss = 0
        self.nbyte = 0
        self.stuffing = False
        self.length = 0
        self.sum = 0
        self.type = 0
        self.lastss = 0
        self.payload = []
        self.datass = 0
        self.nbit = 0
        self.chanvalue = 0
        self.appid = 0
        self.data = 0
        self.lastframees = 0
        self.uplink = False
        self.prim = 0

    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)

    def metadata(self, key, value):
        if key == srd.SRD_CONF_SAMPLERATE:
            pass

    def decode(self, ss, es, data):
        if data[0] == 'FRAME':
            byte = data[2][0]
            if not self.insync:
                if byte == 0x7E:
                    self.insync = True
                else:
                    return
            if self.stuffing:
                self.lastss = ss
                if byte == 0x5D:
                    byte = 0x7D
                elif byte == 0x5E:
                    byte = 0x7E
            else:
                self.lastss = ss

            # we might receive an uplink frame, no 0x7E start byte
            if not self.uplink and not self.inframe and self.type == 1:
                # uplink must be within 3ms
                if self.type == 1 and ss < self.lastframees + 3000:
                    self.uplink = True
                    self.length = byte    # should be 8
                    self.sum = byte
                    self.nbyte = 0
                    self.appid = 0
                    self.data = 0
                    self.put(ss, es, self.out_ann, [1, ['LENGTH', 'L']])
                    return

            if self.uplink:
                self.sum = self.sum + byte
                if self.nbyte == 0:       # type
                    self.type = byte
                    self.put(ss, es, self.out_ann, [3, ['TYPE', 'T']])
                elif self.nbyte == 1:     # prim
                    self.prim = byte
                    self.put(ss, es, self.out_ann, [9, ['PRIM', 'P']])
                    self.ss = ss
                elif self.nbyte >= 2 and self.nbyte < 4:    # appid
                    self.appid = self.appid + byte * 256 ** (self.nbyte - 2)
                    if self.nbyte == 2:
                        self.datass = ss
                    if self.nbyte == 3:
                        self.put(self.datass, es,
                                 self.out_ann,
                                 [10, ['APPID: ' + hex(self.appid),
                                  'APPID', 'A']])
                elif self.nbyte >= 4 and self.nbyte < 8:    # data
                    self.data = self.data + byte * 256 ** (self.nbyte - 4)
                    if self.nbyte == 4:
                        self.datass = ss
                    if self.nbyte == 7:
                        self.put(self.datass, es, self.out_ann,
                                 [11,
                                  ['DATA: ' + str(self.data), 'DATA', 'D']])
                        self.put(self.ss, es, self.out_ann,
                                 [0, ['UPLINK', 'U']])
                elif self.nbyte == 8:     # checksum
                    while self.sum > 0xFF:
                        self.sum = (self.sum >> 8) + (self.sum & 0xFF)
                    if self.sum == 0xFF:
                        self.put(self.lastss, es, self.out_ann,
                                 [4, ['CHECKSUM', 'K']])
                    else:
                        self.put(self.lastss, es, self.out_ann,
                                 [4, ['BAD CHECKSUM', 'BK']])
                    self.uplink = False
                    self.type = 0
                self.nbyte = self.nbyte + 1
            elif (not self.stuffing) and byte == 0x7D:
                self.stuffing = True
            else:
                self.sum = self.sum + byte
                if self.inframe:
                    if not self.stuffing and byte == 0x7E:
                        if self.nbyte == 0:       # just synced maybe?
                            self.put(self.lastss, es, self.out_ann,
                                     [0, ['HEAD', 'H']])
                            self.inframe = True
                            self.nbyte = 0
                            self.sum = 0
                            return
                        self.inframe = False
                        self.payload = []
                        self.lastframees = es
                        if self.nbyte != self.length + 2:
                            self.put(self.lastss, es, self.out_ann,
                                     [0, ['BAD FRAME ' + str(self.nbyte) +
                                          '+' + str(self.length), 'BF']])
                        else:
                            self.put(self.lastss, es, self.out_ann,
                                     [5, ['END', 'E']])
                    elif self.nbyte == 0:
                        self.put(self.lastss, es, self.out_ann,
                                 [1, ['LENGTH', 'L']])
                        self.length = byte
                        self.nbyte = 1
                    elif self.nbyte == 1:
                        self.put(self.lastss, es, self.out_ann,
                                 [2, ['TYPE', 'T']])
                        self.type = byte
                        self.nbyte = 2
                    else:
                        if self.nbyte == 2:
                            self.ss = ss
                        self.payload.append(byte)
                        self.nbyte = self.nbyte + 1
                        if self.nbyte == self.length + 1:
                            if self.type == 0:
                                self.put(self.ss, es, self.out_ann,
                                         [3, ['CHANNEL DATA',
                                              'CHANNELS', 'CHAN', 'C']])
                            elif self.type == 1:
                                self.put(self.ss, es, self.out_ann,
                                         [6, ['DOWNLINK', 'D']])
                        if self.nbyte == self.length + 2:
                            while self.sum > 0xFF:
                                self.sum = (self.sum >> 8) + (self.sum & 0xFF)
                            if self.sum == 0xFF:
                                self.put(self.lastss, es, self.out_ann,
                                         [4, ['CHECKSUM', 'K']])
                            else:
                                self.put(self.lastss, es, self.out_ann,
                                         [4, ['BAD CHECKSUM', 'BK']])
                else:
                    if (not self.stuffing) and byte == 0x7E:
                        self.put(self.lastss, es, self.out_ann,
                                 [0, ['HEAD', 'H']])
                        self.inframe = True
                        self.nbyte = 0
                        self.sum = 0
                        self.data = 0
                        self.appid = 0
                self.stuffing = False
        elif data[0] == 'DATA':
            if self.type == 0:
                bits = data[2][1]
                if self.nbyte == 24:
                    ch17 = bits[0][0]
                    ch18 = bits[1][0]
                    framelost = bits[2][0]
                    failsafe = bits[3][0]
                    flags = 'CH17:' + str(ch17) + ' CH18:' + str(ch18) +\
                        ' FRAMELOST:' + str(framelost) + ' FAILSAFE:' +\
                        str(failsafe)
                    self.put(bits[0][1], bits[7][2], self.out_ann,
                             [8, ['FLAGS', flags]])
                elif self.nbyte == 25:
                    self.put(bits[0][1], bits[7][2], self.out_ann,
                             [8, ['RSSI', 'RSSI: ' + str(data[2][0])]])
                elif self.nbyte == 2:
                    self.nbit = 0
                if self.nbyte >= 2 and self.nbyte < 24:
                    for i in range(8):
                        if math.floor(self.nbit / 11) < 16:
                            if self.nbit % 11 == 0:
                                self.datass = bits[i][1]
                                self.chanvalue = 0
                            self.chanvalue = self.chanvalue +\
                                bits[i][0] * (1 << (self.nbit % 11))
                            if self.nbit % 11 == 10:
                                label = 'CH' +\
                                        str(1 + math.floor(self.nbit / 11))
                                longlabel = label + ': ' + str(self.chanvalue)
                                self.put(self.datass,
                                         bits[i][2], self.out_ann,
                                         [8, [label, longlabel]])
                        self.nbit = self.nbit + 1
            elif self.type == 1:
                if self.nbyte == 2:
                    self.put(ss, es, self.out_ann, [9, ['PRIM', 'P']])
                elif self.nbyte == 3:
                    self.datass = ss
                    self.appid = data[2][0]
                elif self.nbyte == 4:
                    self.appid = self.appid * 256 + data[2][0]
                    self.put(self.datass, es, self.out_ann,
                             [10, ['APPID: ' + hex(self.appid), 'APPID', 'A']])
                elif self.nbyte > 4 and self.nbyte <= 8:
                    self.data = self.data * 256 + data[2][0]
                    if self.nbyte == 5:
                        self.datass = ss
                    if self.nbyte == 8:
                        self.put(self.datass, es, self.out_ann,
                                 [10, ['DATA: ' + str(self.data),
                                       'DATA', 'D']])
