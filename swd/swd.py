from machine import Pin
import time
import micropython

class swd:
    DP_ABORT =const(0x00)#w
    DP_IDCODE =const(0x00)#r
    DP_CTRLSTAT =const(0x04)#rw
    DP_SELECT =const(0x08)#w   aa 00 00 00 bx x=0/1 ctrlsel for dp ctrl/WCR
    DR_RESEND =const(8)#r
    DP_RDBUFF =const(0x0c)
    
    # bank 0
    AP_CSW =const(0x00)
    AP_TAR =const(0x04)
    #8 reserved
    AP_DRW =const(0x0c)
    
    # a7:4 selects bank - from select reg
    # bank 1
    AP_BD0 =const(0x10)
    AP_BD1 =const(0x14)
    AP_BD2 =const(0x18)
    AP_BD3 =const(0x1c)
    
    #bank f
    # f0 reserved
    AP_CFG =const(0xf4)
    AP_DBGDRAR =const(0xf8)
    AP_IDR =const(0xfc)
    
    def __init__(self):
        self.clk = Pin(14, Pin.OUT, value=1)
        self.dio = Pin(13, Pin.IN, Pin.PULL_UP)
        self.turn=0
        
    def init(self):
        self.write(0xffffffff,32)
        self.write(0xffffffff,32)
        self.write(0xe79e,32)
        self.write(0xffffffff,32)
        self.write(0xffffffff,32)
        self.write(0,32)
        self.write(0,32)
        
        idcode = self.DP_Read(DP_IDCODE)
        return idcode

    def DP_Read(self,addr):
        return self.doread(addr,0)
    def AP_Read(self,addr):
        return self.doread(addr,1)
            
    def doread(self,addr,ap):
        retry=15
        while retry>0:
            retry-=1
            (ack,d)=self.transfer(addr,ap,1)
            if ack==1:
                return d
            if ack==4:
                self.processFault()
            if ack!=2:
                raise Exception("bad ack:{0}".format(ack))
        raise Exception("timeout:{}".format(ack))

    def DP_Write(self,addr,data):
        return self.dowrite(addr,0,data)
    def AP_Write(self,addr,data):
        return self.dowrite(addr,1,data)
    
    def dowrite(self,addr,ap,data):
        retry=15
        while retry>0:
            retry-=1
            (ack,d)=self.transfer(addr,ap,0,data)
            if ack==1:
                return d
            if ack==4:
                self.processFault()
            if ack!=2:
                raise Exception("bad ack:{0}".format(ack))
        if ack==2:
            self.clearSticky(1) # DAPABORT
        raise Exception("timeout:{}".format(ack))

    def processFault(self):
        (ack,d)=(1,self.readStatus())
        if ack!=1:
            raise Exception("failed to get error status")
        if d&0x20: # stickyerr
            self.clearSticky(4)
        if d&0x10: #stickycmp
            self.clearSticky(2)
        if d&2: # stickyorun
            self.clearSticky(0x10)
        if d&0x80: #wdataerr
            self.clearSticky(8)

    @micropython.viper
    @staticmethod
    def calcparity(d:int) -> int:
        d = (d&0xffff) ^ ((d>>16)&0xffff)
        d = (d&0xff) ^ (d>>8)
        d = (d&0xf) ^ (d>>4)
        d = (d&0x3) ^ (d>>2)
        d = (d&1) ^ (d>>1)
        return d
    
    @micropython.native
    def transfer(self,addr, APorDP, RorW, data=0):
        # 1 0 p a a r a 1
        filledaddr=0x81 | ((addr & 0xc)<<1)
        if addr&8:
            filledaddr^=0x20
        if addr&4:
            filledaddr^=0x20
        if APorDP:
            filledaddr^=0x22
        if RorW:
            filledaddr^=0x24
        self.write(filledaddr,8)
        a=self.read(3)
        if a==1:
            if (RorW):
                d=self.read(32)
                p=self.read(1)
                c=swd.calcparity(d)
                if c!=p:
                    raise Exception("parity error")
                self.write(0,8)
                return (a,d)
            else:
                self.write(data,32)
                p=swd.calcparity(data)
                self.write(p,1)
                self.write(0,8)
                return (a,None)
        else:
            # 1=ok, 2=wait, 4=fault - 7=?protoerror
            print("{1} {2} {3} {4} {5} status:{0}".format(a, addr, APorDP, RorW, hex(filledaddr), hex(data)))
        self.write(0,32)
        return (a,None)

    @micropython.native
    def doturn(self,WorR):
        # 1=write
        self.dio(1)
        self.dio.init(Pin.IN,pull=Pin.PULL_UP)#, Pin.PULL_UP)
        self.clk(0)
        time.sleep_us(2)
        self.clk(1)
        time.sleep_us(2)
        if WorR:
            self.dio.init(Pin.OUT)
        self.turn = WorR
        
    @micropython.native
    def write(self,v,b):
        if self.turn == 0:
            self.doturn(1)
        d=self.dio
        c=self.clk
        while b>0:
            b-=1
            d(v&1)
            c(0)
            time.sleep_us(2)
            v>>=1
            c(1)
            time.sleep_us(2)
            
    @micropython.native
    def read(self,b):
        if self.turn==1:
            self.doturn(0)
        i=1
        v=0
        d=self.dio
        c=self.clk
        while b>0:
            b-=1
            if d():
                v|=i
            c(0)
            time.sleep_us(2)
            i<<=1
            c(1)
            time.sleep_us(2)
        return v
    
    def readStatus(self):
        (ack,d) = self.transfer(DP_CTRLSTAT,0,1)
        if ack!=1:
            raise Exception("Failed to get status:{}".format(ack))
        return d

    def clearSticky(self,bit):
        (ack,d)=self.transfer(DP_ABORT,0,0,bit)
        if ack!=1:
            raise Exception("Failed to clear sticky")

        


class DP:
#    DP_ABORT =const(0x00)#w
#    DP_IDCODE =const(0x00)#r
#    DP_CTRLSTAT =const(0x04)#rw
#    DP_SELECT =const(0x08)#w   aa 00 00 00 bx x=0/1 ctrlsel for dp ctrl/WCR
#    DR_RESEND =const(8)#r
#    DP_RDBUFF =const(0x0c)

    def __init__(self,swd):
        self.swd=swd
        swd.select=0xbad
        
    def setPower(self, sys=True, dbg=True):
        data = 0
        if sys:
            data|=0x40000000
        if dbg:
            data|=0x10000000
        (ack,d)=self.swd.transfer(DP_CTRLSTAT,0,0,data)
        if ack!=1:
            raise Exception("Failed set power")

    def setSelect(self,ap,bank=0):
        d=((ap & 0xff)<<24)|((bank&0xf)<<4)
        if d!=self.swd.select:
            self.write(DP_SELECT,d)
            self.swd.select=d
            
    def read(self, addr):
        return self.swd.DP_Read(addr)

    def write(self, addr, data):
        self.swd.DP_Write(addr, data)

class AP:
    def __init__(self,dp,ap):
        self.swd=dp.swd
        self.dp=dp
        self.ap=ap
        
    def read(self, addr):
        self.dp.setSelect(self.ap, addr>>4)
        t1=self.swd.AP_Read( addr & 0xf )
        t2=self.swd.DP_Read( DP_RDBUFF )
        return t2
    
    def write(self, addr, data):
        self.dp.setSelect(self.ap, addr>>4)
        self.swd.AP_Write( addr & 0xf, data )
        
    def read_idr(self):
        return self.read(swd.AP_IDR)

class MEMAP(AP):
    # bank 0
    MEM_AP_CSW =const(0x00)
    MEM_AP_TAR =const(0x04)
    #8 reserved
    MEM_AP_DRW =const(0x0c)
    
    # a7:4 selects bank - from select reg
    # bank 1
    MEM_AP_BD0 =const(0x10)
    MEM_AP_BD1 =const(0x14)
    MEM_AP_BD2 =const(0x18)
    MEM_AP_BD3 =const(0x1c)
    
    MEM_AP_BASE=const(0xf8)

    def __init__(self,dp,ap):
        super().__init__(dp,ap)
        self.idr=self.read_idr()
        print("idr={0:x} des={1:x} cls={2:x}".format(self.idr, (self.idr>>17)&0x7ff, (self.idr>>13)&0xf))
        cls=(self.idr>>13)&0xf
        if cls!=0x8:
            raise Exception("Not mem ap")

    def read_csw(self):
        return self.read(MEM_AP_CSW)

    def setCsw(self, v):
        v|=0x23000040
        self.write(MEM_AP_CSW, v)
    
    def read_base(self):
        base=self.read(MEM_AP_BASE)
        if base&3!=3:
            raise Exception("no base")
        return base&0xfffffff0

    
    def _read_mem(self,sz,addr):
        self.setCsw(sz)
        self.write(MEM_AP_TAR,addr)
        return self.read(MEM_AP_DRW)

    def read_mem(self,addr):
        return self._read_mem(2,addr)
    
    def read_mem16(self,addr):
        return self._read_mem(1,addr)

    def read_mem8(self,addr):
        return self._read_mem(0,addr)

    def _write_mem(self, addr, sz, data):
        self.setCsw(sz)
        self.write(MEM_AP_TAR,addr)
        self.write(MEM_AP_DRW, data)

    def write_mem(self, addr, data):
        self._write_mem(addr, 2, data)
    def write_mem16(self, addr, data):
        self._write_mem(addr, 1, data)
    def write_mem8(self, addr, data):
        self._write_mem(addr, 0, data)

    def read_mem_block(self, addr, buffer):
        self.setCsw(0x12)
        self.write(MEM_AP_TAR,addr)
        t1=self.swd.AP_Read(MEM_AP_DRW)
        for n in range(len(buffer)/4):
#            d = self.swd.DP_Read(DP_RDBUFF)
            d = self.swd.AP_Read(MEM_AP_DRW)
            buffer[n*4]=d&0xff
            buffer[n*4+1]=(d>>8)&0xff
            buffer[n*4+2]=(d>>16)&0xff
            buffer[n*4+3]=(d>>24)&0xff

    def write_mem_block(self, addr, buffer):
        self.setCsw(0x12)
        self.write(MEM_AP_TAR,addr)
        for n in range(len(buffer)/4):
#            d = self.swd.DP_Read(DP_RDBUFF)
            d=buffer[n*4]|buffer[n*4+1]<<8|buffer[n*4+2]<<16|buffer[n*4+3]<<24
            self.swd.AP_Write(MEM_AP_DRW,d)


if __name__ == "__main__":
    rst=Pin(26,Pin.OUT)
    rst(0)
        
    time.sleep_ms(300)
    rst(1)
    
    s=swd()
    i=s.init()
    print("idcode={0:x}".format(i))
    dp=DP(s)
    dp.setPower()
    #p=s.readStatus()
#    print("ctrl Status={0:x}".format(p))

    m=MEMAP(dp,0)
    # halt
    m.write_mem(0xe000edf0,0xA05F0003)
    csw=m.read_csw()
    print("csw={0:x}".format(csw))
    
    v=m.read_mem(0)
    print(hex(v))

    a=0x0000000
    b=bytearray(64)
    m.read_mem_block(a,b)
    print("-".join(hex(d) for d in b))

    m.read_mem_block(a,b)
    print("-".join(hex(d) for d in b))
    
    
