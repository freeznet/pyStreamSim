#!/user/bin/env python
#-*- encoding:utf-8 -*-
import socket
import sys
import os
import time
import urllib
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation 
from threading import Thread


sockIndex = 1
serverList = [['218.92.0.22',1234],['42.121.78.93',1234],['106.186.17.248',1234],['106.186.20.75',1234],['127.0.0.1',1234]]

rateList = [300,700,1500,2500,3500,7000]
playTime = 5 * 128

dataPacket = [len('\x01'*rateList[0]*playTime), len('\x01'*rateList[1]*playTime), len('\x01'*rateList[2]*playTime), len('\x01'*rateList[3]*playTime), len('\x01'*rateList[4]*playTime), len('\x01'*rateList[5]*playTime)]
# 
downloadDoneList = []
downloadDonePendList = []

bufferLength = 0;
nowFragID = 0;

maxFragNum = 8
nowBlock = 0
blockList = []

qmin = 10
qmax = 45

slist = None

fig1 = None
fig2 = None

timelineData = []
bufferLengthData = []
rateData = []
rateTimelineData = []

allStartTime = 0

class Server():
    def __init__(self, id, name):
        self.id = id
        self.bw = 0
        self.name = name
        self.downloadFrag = []
        self.downloadBlock = []
        self.downloadedFrag = []
        self.numofrequest = 0
    def getBandwidth(self):
        return self.bw
    def assignFrag(self, f):
        if(f not in self.downloadFrag):
            self.downloadFrag.append(f)
    def assignBlock(self, b):
        if(b not in self.downloadBlock):
            self.downloadBlock.append(b)
    def getDownloadFragment(self):
        if(len(self.downloadFrag)>0):
            return self.downloadFrag[0]
        else:
            return None
    def setDownloaded(self, f):
        if(f in self.downloadFrag):
            self.downloadedFrag.append(f)
            self.downloadFrag.remove(f)

class ServerList():
    def __init__(self):
        self.list = []
    def addServer(self, s):
        if(s not in self.list):
            self.list.append(s)
    def getServer(self, i):
        return self.list[i]
    def resort(self):
        if(self.list[0] != None and len(self.list)>1):
            leng = len(self.list)
            for i in xrange(leng):
                for j in xrange(leng - 1 - i):
                    if(self.list[j].getBandwidth() < self.list[j+1].getBandwidth()):
                        temp = self.list[j]
                        self.list[j] = self.list[j+1]
                        self.list[j+1] = temp
        #for i in range(0,leng):
        #    print i,'->',self.list[i].name,'->',self.list[i].bw


class Block():
    def __init__(self, id, serverlist, rate, playtime):
        global maxFragNum
        self.id = id
        self.servers = serverlist
        self.serverSize = len(serverlist.list)
        self.fragList = []
        self.fragNum = 0
        self.rate = rate
        self.playtime = playtime
        self.isDone = False
        self.startTime = 0
        self.endTime = 0
        self.startBuffer = 0
        self.endBuffer = 0
        self.downDoneSeq = []
        cmin = serverlist.list[self.serverSize-1].getBandwidth()
        while True:
            serverlist.list[-1].numofrequest = 1
            self.fragNum = 1
            for i in range (0,self.serverSize-1):
                ci = serverlist.getServer(i).getBandwidth()
                serverlist.getServer(i).numofrequest = int(self.myFloor(ci,cmin))
                #print i,serverlist.getServer(i).numofrequest
                self.fragNum = self.fragNum + serverlist.getServer(i).numofrequest
            if(self.fragNum>maxFragNum):
                self.serverSize = self.serverSize - 1
                cmin = serverlist.list[self.serverSize-1].getBandwidth()
            else:
                break
        #print self.fragNum
        for i in range(0,self.fragNum):
            self.initFragment(i)
        self.doSchedule()

    def initFragment(self, i):
        f = Fragment(i, self.rate, self.playtime, self)
        self.fragList.append(f)

    def doSchedule(self):
        Nk = self.fragNum
        Smax = self.serverSize
        #print 'Nk=',Nk,'Smax=',Smax
        x = [[0 for col in range(Nk)] for row in range(Smax)]
        for i in range(0,Nk):
            jstar = 0
            jlist = [0 for row in range(Smax)]
            for j in range(0, Smax):
                jlist[j] = 1 / self.servers.getServer(j).getBandwidth()
                for t in range(0,i) :
                    jlist[j] += x[j][t] * (1 / self.servers.getServer(j).getBandwidth());
            jstar = jlist.index(min(jlist))
            #print 'jstar=',jstar,'i=',i
            x[jstar][i] = 1
            f = self.fragList[i]
            if(f != None):
                f.setDownloadBy(self.servers.getServer(jstar))
                self.servers.getServer(jstar).assignFrag(f)
        self.x = x
        # for i in range(0,Smax):
        #     for j in range(0, Nk):
        #         print x[i][j],
        #     print ""
    def getX(self, server, frag):
        return self.x[server][frag]


    def myFloor(self, a, b):
        t = a / b
        x = math.floor(t)
        if(t-x>0.8):
            x = x + 1
        return x
    def getalphan(self, n):
        ret= 0
        p = 0
        q = 0
        f = self.fragList[n]
        for i in range(0, self.serverSize):
            q = q + self.getX(i, n) * f.downBw
        for j in range(0, self.serverSize):
            t = self.getX(j, n)
            m = 0
            for i in range(0,n+1):
                m = m + self.getX(j, i)
            p = p + (t * m)
        ret = p / q
        return ret
    def getNewRateID(self, rate):
        global rateList
        ret = 0
        temp = rateList[0]
        for i in range(0,len(rateList)):
            if(rateList[i]<=rate):
                temp = rateList[i]
                ret = i
        return ret

    def getNewRate(self):
        global blockList, qmin, qmax
        pRate = rateList[self.rate-1]
        newSelect = 0
        kP = 1.1
        kD = 0.8
        if(len(blockList)>=2):
            lastBlock = blockList[-2]
            if(self.endBuffer >= qmax or self.endBuffer <= qmin):
                vk = [0 for col in range(self.fragNum)]
                if(self.endBuffer <= qmin):
                    q0 = qmin
                elif(self.endBuffer >= qmax):
                    q0 = qmax
                for i in range (0,self.fragNum):
                    f = self.fragList[i]
                    alphaN = self.getalphan(i)
                    q_fragtEnk = f.endBuffer
                    q_blockSk = self.startBuffer
                    q_blockEk = self.endBuffer
                    fragDownDur = f.downDur
                    #print f.id,alphaN,q_fragtEnk,q_blockSk,q_blockEk,fragDownDur
                    vk[i] = ((1/(self.playtime*alphaN)) * kP * (q_blockEk - q0))+ ((1/(self.playtime*alphaN)) * kD * ((q_fragtEnk - q_blockSk) / (fragDownDur)));
                if(self.endBuffer <= qmin):
                    vtemp = min(vk)
                elif(self.endBuffer >= qmax):
                    vtemp = max(vk)

                newRate = pRate + vtemp
                #print 'vtemp = ',vtemp, 'newRate = ',newRate
                newSelect = self.getNewRateID(newRate) + 1
                if(self.endBuffer<=qmin and newSelect>self.rate):
                    newSelect = self.rate;
                elif(self.endBuffer>=qmax and newSelect<self.rate):
                    newSelect = self.rate;
                return newSelect
        return self.rate




class Fragment():
    def __init__(self, id, rate, playtime, block):
        self.id = id
        self.rate = rate
        self.rateInt = rateList[rate-1]
        self.playtime = playtime
        self.startDownload = 0
        self.endDownload = 0
        self.startBuffer = 0
        self.endBuffer = 0
        self.downDur = 0
        self.block = block
        self.downBy = None
        self.isDone = False
        self.downBw = 0
    def setDownloadBy(self, server):
        self.downBy = server
    def setDownloadDone(self):
        self.isDone = True
        self.block.downDoneSeq.append(self)
        allDone = True
        for f in self.block.fragList:
            if(f.isDone==False):
                allDone = False
        self.block.isDone = allDone



class Buffer(Thread):
    def __init__(self):
        global slist, nowBlock
        Thread.__init__(self, name="buffer")
        self.bufferLength = 0
        

    def run(self):
        global slist, nowBlock, bufferLength, rateList
        global timelineData, bufferLengthData, rateData, fig1, fig2, allStartTime, rateTimelineData
        while True:
            if(len(blockList)==0):
                flg = False
                for ser in slist.list:
                    if(ser.getBandwidth()==0 or ser.getBandwidth()==None):
                        flg = True
                # start init first block
                if(flg == False):
                    slist.resort()
                    b = Block(nowBlock, slist, 1, 5)
                    b.startTime = time.time()
                    b.startBuffer = bufferLength
                    timelineData.append(time.time() - allStartTime)
                    bufferLengthData.append(bufferLength)
                    rateTimelineData.append(time.time() - allStartTime)
                    rateData.append(rateList[0])
                    blockList.append(b)
                    print 'block',nowBlock,' -> ',b.fragNum
                    nowBlock = nowBlock + 1
            elif(len(blockList)<20):
                myBlock = blockList[-1]
                if(myBlock != None and myBlock.isDone==True):
                    myBlock.endTime = time.time()
                    
                    #print frag & compute buffer
                    myBufferLength = myBlock.startBuffer
                    nowProcee = 0
                    print 'Server','\t','FragID','\t','Rate','\t\t','Down Dur','\t\t','Bandwidth','\t\t','BufferLength'
                    while nowProcee<myBlock.fragNum:
                        nowpro = 0
                        nowtime = 0
                        for fra in myBlock.downDoneSeq:
                            # if(fra.id > nowProcee):
                            #     nowpro = nowpro + 5
                            if(fra.id==nowProcee and fra.downDur>=nowtime):
                                fra.endBuffer = myBufferLength + 5 - fra.downDur
                                nowtime = fra.downDur
                                myBufferLength = fra.endBuffer
                                nowProcee = nowProcee + 1 
                                print fra.downBy.name,'\t',fra.id,'\t',fra.rateInt,'\t',fra.downDur,'\t',fra.downBw,'KB/s\t',fra.endBuffer
                                break
                            elif(fra.id==nowProcee and fra.downDur<nowtime):
                                fra.endBuffer = myBufferLength + 5
                                #nowtime = fra.downDur
                                myBufferLength = fra.endBuffer
                                nowProcee = nowProcee + 1 
                                print fra.downBy.name,'\t',fra.id,'\t',fra.rateInt,'\t',fra.downDur,'\t',fra.downBw,'KB/s\t',fra.endBuffer
                                break
                    for fra in myBlock.downDoneSeq:
                        if(rateData[-1]!=fra.rateInt):
                            rateData.append(rateData[-1])
                            rateTimelineData.append(fra.endDownload - allStartTime)
                        timelineData.append(fra.endDownload - allStartTime)
                        bufferLengthData.append(fra.endBuffer)
                        rateTimelineData.append(fra.endDownload - allStartTime)
                        rateData.append(fra.rateInt)
                    bufferLength = myBlock.fragList[-1].endBuffer
                    #start init new block
                    myBlock.endBuffer = bufferLength
                    slist.resort()
                    newSelect = myBlock.getNewRate()
                    #print 'getNew Select',newSelect
                    b = Block(nowBlock, slist, newSelect, 5)
                    b.startTime = time.time()
                    b.startBuffer = bufferLength
                    blockList.append(b)
                    print 'block',nowBlock,' -> ',b.fragNum
                    nowBlock = nowBlock + 1
            elif(fig1==None):
                fig1 = plt.subplot(211)
                fig1.plot(timelineData, bufferLengthData)
                print rateData
                print timelineData
                fig2 = plt.subplot(212)
                fig2.plot(rateTimelineData,rateData)
                plt.show()
            else:
                break



class serverConnect(Thread):
    def __init__(self, threadname, serverID,  rate, ptime):
        global slist
        Thread.__init__(self, name=threadname)
        self.name = threadname
        self.nowRate = rate
        self.playTime = ptime
        self.downloaded = []
        self.server = serverID
        self.conn = 0
        self.s = Server(serverID, threadname)
        slist.addServer(self.s)

    def recv_timeout(self,rate,timeout=2):
        self.conn.setblocking(0)
        total_data=[];
        data='';
        recvLen = 0
        begin=time.time()
        start= time.time()
        dur = 0
        so = "SEND" + "%d" % rate
        self.conn.send(so)
        while 1:
            if total_data and time.time()-begin > timeout:
                break
            elif time.time()-begin > timeout*2:
                break
            elif recvLen>=dataPacket[rate-1]:
                break
            try:
                data = self.conn.recv(8192)
                if data:
                    total_data.append(data)
                    recvLen = recvLen + len(data)
                    begin = time.time()
                #else:
                #    time.sleep(0.01)
            except:
                pass
        #print 'length =' , recvLen,', time =' , dur, 'bw =' , recvLen/8/dur
        dur = time.time() - start
        return recvLen,dur

    def getLastDoneFrag():
        global downloadDoneList
        if(len(downloadDoneList)>0):
            return downloadDoneList[-1]
        else:
            return None

    def computeBuffer(self, frag):
        global downloadDoneList
        global bufferLength
        global downloadDonePendList
        last = getLastDoneFrag()
        if(last!=None and last.id+1 == frag.id):
            downloadDoneList.append(frag)
            bufferLength = bufferLength + frag.playtime - frag.downDur
            if(frag in downloadDonePendList):
                downloadDonePendList.remove(frag)

    def run(self):
        global nowFragID
        global bufferLength
        global slist
        rate = 1
        #test speed
        if(self.s.getBandwidth()==None or self.s.getBandwidth()==0):
            self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.conn.connect((serverList[self.server][0], serverList[self.server][1]))
            rev, d = self.recv_timeout(1)
            if(rev>0 and d>0):
                print 'BW Testing:',self.name,'=' , rev/1024/d, 'KB/s'
                self.s.bw = rev/1024/d
        nowFrag = self.s.getDownloadFragment();
        while True:
            if(nowFrag!=None):
                self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.conn.connect((serverList[self.server][0], serverList[self.server][1]))
                nowFrag.startDownload = time.time()
                nowFrag.startBuffer = bufferLength
                rate = nowFrag.rate;
                rev, d = self.recv_timeout(rate)
                nowFrag.endDownload = time.time()
                if(rev>0 and d>0):
                    #bufferLength = bufferLength + 5 - d
                    #print self.name,nowFrag.id,nowFrag.rateInt,d,int(rev/1024/d),bufferLength
                    self.s.bw = rev/1024/d
                    nowFrag.downBw = self.s.bw
                    nowFrag.downDur = d
                    nowFrag.setDownloadDone()
                    #nowFrag.endBuffer = bufferLength
                    self.s.setDownloaded(nowFrag)
                    self.downloaded.append(nowFrag)
            nowFrag = self.s.getDownloadFragment();
                    
                

def connToServer ():
    global sockIndex
    #创建一个socket连接到127.0.0.1:8081，并发送内容
    
    rate = 1
    while True:
    #等待服务端返回数据，并输出
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.connect((serverList[0][0], serverList[0][1]))
        rev = recv_timeout(conn,rate)
        rate = rate + 1
        if rate>6:
            rate = 6
        
def start(numT):
    global allStartTime
    allStartTime = time.time()
    threadname = [ "server_%d" % i for i in range(0, numT) ]
    tasks = []
    for i in range(0,numT):
        task = serverConnect( threadname[i], i, 1, 5 )
        #task.setDaemon( True )
        task.start()
        tasks.append( task )
    task = Buffer()
    task.start()
    tasks.append( task )

if __name__ == '__main__':
    #plt.interactive(True)
    
    slist = ServerList()
    start(3)
