import micropython
import swd

class samd:
    RAM_BASE=const(0x20000000)
    NVM_BASE=const(0x41004000)

    def __init__(self):
        self.swd=swd.swd()
        
    def init(self):
        id=self.swd.init()
        if id==0xbc11477:
            self.dp=swd.DP(self.swd)
            self.dp.setPower()
            self.m=swd.MEMAP(self.dp,0)

            st = self.swd.readStatus()
            # power on
            print("Status:{0:x}".format(st))
        else:
            print("failed")
    
    def nvm_cmd(self,cmd):
        self.m.write_mem16(NVM_BASE, 0xa500 | cmd)
    def nvm_waitready(self):
        while True:
            s=self.m.read_mem8(NVM_BASE+0x14)
            if s:
                break
        if s&2:
            raise Exception("nvm error:{0}".format(s))
    def nvm_getPageSz(self):
        v=self.m.read_mem(NVM_BASE+8)
        return  (8<<((v>>16)&7),v&0xffff)
    def nvm_setAddr(self,addr):
        self.m.write_mem(NVM_BASE+0x1c,addr>>1)
    def nvm_getStatus(self):
        return self.m.read_mem16(NVM_BASE+0x18)
    def nvm_clearStatus(self,d):
        return self.m.write_mem16(NVM_BASE+0x18,d)

    def read_userRow(self):
        cfg=self.m.read_mem(0x804000)
        cfg1=self.m.read_mem(0x804004)
        return (cfg1<<32)|cfg

    def read_cal(self):
        cfg=self.m.read_mem(0x806020)
        cfg1=self.m.read_mem(0x806024)
        l=((cfg1&7)<<5)|((cfg>>27)&31)
        b=(cfg1>>3)&7
        o=(cfg1>>6)&127
        d=(cfg1>>26)&63
        return (l,b,o,d)

    def halt(self, h=True):
        v=0xA05F0000 | (3 if h else 0)
        self.m.write_mem(0xe000edf0,v)

    def listap(self):
        a=swd.AP(self.dp,0)
        for n in range(3):
            a.ap=n
            t = a.read_idr()
            if t is None:
                print("{0}=idr failed".format(n))
            elif t!=0:
                print("{1}=idr={0:08x}".format(t,n))
    
    def dumpToFile(self,addr,l,fn):
        b=bytearray(0x100)
        f=open(fn,"wb")
        for n in range(l/len(b)):
            print("addr={0:x}".format(addr+n*0x100))
            self.m.read_mem_block(addr+n*0x100,b)
            f.write(b)
        f.close()
    
    def dumpRom(self):
        sz = self.nvm_getPageSz()
        addr=0
        l = sz[0]*sz[1]
        self.dumpToFile(addr,l,"img.bin")

    def dumpRam(self):
        l = 4*1024
        self.dumpToFile(RAM_BASE,l,"ram.bin")
    
    def dumpBase(self):
        base = s.m.read_base()
        print("base={0:x}".format(base))
        n=0
        while n<10:
            addr = self.m.read_mem(base+n*4)
            if addr==0:
                break
            print("entry:{0:x} {1:x}".format(addr&0xf, addr>>12))
            n+=1

        n=0
        while n<4:
            data = self.m.read_mem(base+0xff0+n*4)
            print("cir:{0:x} {1:x}".format(n, data))
            n+=1
        
        self.dumpToFile(base,0x1000,"core.bin")
    
    def erase(self,addr,pgsz,cnt):
        for c in range(cnt):
            self.nvm_setAddr(addr)
            self.nvm_cmd(0x2)
            self.nvm_waitready()
            addr+=pgsz

    def prog(self,addr,fn):
        ctrl=self.m.read_mem(NVM_BASE+4)
        if ctrl&128:
            print("manual write")
        else:
            print("auto write")
        (pgSz,cnt)=self.nvm_getPageSz()
        print("Page sz={0} cnt={1}".format(pgSz,cnt))
        f=open(fn,"rb")
        self.erase(0,pgSz,cnt)
        while cnt>0:
            cnt-=1
            b=f.read(pgSz)
            print("addr={0:x} {1}".format(addr,len(b)))
            if b is None or len(b)==0:
                print("ended")
                break
            if len(b) != pgSz:
                # clear buffer
                self.nvm_cmd(0x44)
                self.nvm_waitready()

            self.m.write_mem_block(addr,b)

            if ctrl&128 or len(b)!=pgSz:
                # need manual write
                # write
                self.nvm_setAddr(addr)
                self.nvm_cmd(0x4)
                self.nvm_waitready()
            else:
                self.nvm_waitready()

            if len(b) != pgSz:
                print("len={0}".format
                      (len(b)))
                break
            addr+=pgSz
