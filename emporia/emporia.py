import machine
import struct
import uctypes

i2c = machine.SoftI2C(scl=machine.Pin(22), sda=machine.Pin(21),freq=100000)

cc={"ver":uctypes.UINT8|0, "unk1":uctypes.UINT8|1, "unk2":uctypes.UINT8|2, "cnt":uctypes.UINT8 | 3}
cc["pwr"]=(uctypes.ARRAY|4,19,{"p1":uctypes.INT32|0,"p2":uctypes.INT32|4,"p3":uctypes.INT32|8})
cc["cur"]=(uctypes.ARRAY|0xf4,19|uctypes.UINT16)
cc["v"]=(uctypes.ARRAY|0xe8,3|uctypes.UINT16)
cc["hz"]=uctypes.UINT16|0xee
cc["p1"]=uctypes.UINT16|0xf0
cc["p2"]=uctypes.UINT16|0xf2
cc["end"]=uctypes.UINT16|0x11c

current_factor = 55
calibration = 0.022
freq_base = 26000.0


def readRaw():
    return i2c.readfrom(100, 284)

def read():
    d=readRaw()
    c=uctypes.struct(uctypes.addressof(d),cc, uctypes.LITTLE_ENDIAN)
    return c

def printHdr():
    c=read()
    print("ver:",c.ver," cnt:", c.cnt)

def printHdr2():
    c=read()
    print("ver:%d u1:%d u2:%d cur:%d" % c.ver,c.unk1,c.unk2,c.cnt)

def printVolt():
    c=read()
    print("v1:%d v2:%d v3:%d hz:%d p1:%d p2%d" % (c.v[0],c.v[2],c.v[2],c.hz,c.p1,c.p2))

def printCurrent():
    c=read()
    for i in range(19):
        print("%d) %d %d %d %d" % (i,c.pwr[i].p1,c.pwr[i].p2,c.pwr[i].p3,c.cur[i]))
        
def printData():
    c=read()
    print("v1:%d v2:%d v3:%d hz:%d p1:%d p2%d" % (c.v[0],c.v[2],c.v[2],c.hz,c.p1,c.p2))
    for i in (0,3):
        print("%d) %d %d %d %d" % (i,c.pwr[i].p1,c.pwr[i].p2,c.pwr[i].p3,c.cur[i]))
    
def getJson():
    c=read()
    ret = {"seq":c.cnt,"v1":c.v[0]*calibration,"v2":c.v[1]*calibration,"v3":c.v[2]*calibration}
    ret["hz"] = round(freq_base/c.hz,1)
    ret["p1"] = 360*c.p1/c.hz
    ret["p2"] = 360*c.p2/c.hz
    for i in range(19):
        if c.cur[i] > 20000:
            continue
        val = c.cur[i] / current_factor
        if i < 3:
            name = "in%d" % i
        else:
            name = "cir%d" % (i-3)
            val = val / 4
        ret[name] = val
    return ret
    