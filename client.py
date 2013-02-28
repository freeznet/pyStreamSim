#!/user/bin/env python
#-*- encoding:utf-8 -*-
import socket
import sys
import os
from time import time, sleep
import urllib
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation 
from threading import Thread


sockIndex = 1
#serverList = [['42.121.132.130',1234],['42.121.14.186',1234],['42.121.14.193',1234],['60.28.160.80',1234],['sh.idcst.cn',1234],['49.212.204.220',1234],['sh.idcst.cn',1234]]
#serverList = [['42.121.14.193',12345],['42.121.14.186',1234],['42.121.125.177',12345],['60.28.160.80',1234],['sh.idcst.cn',1234],['49.212.204.220',1234],['sh.idcst.cn',1234]]
serverList = [['plab1.cs.ust.hk',1234],['planetlab2.cqupt.edu.cn',1234],['planetlab-1.sjtu.edu.cn',1234],['plink.cs.uwaterloo.ca',1234],['planetlab1.cs.colorado.edu',1234],['151.97.9.224',1234]]
#serverList = [['127.0.0.1',1234],['127.0.0.1',1235],['127.0.0.1',1236]]
serverLimit = [62.5* 8 * 1024,125* 8 * 1024,187.5* 8 * 1024]

rateList = [300,700,1500,2500,3500]
playTime = 5 * 128

dataPacket = [len('\x01'*rateList[0]*playTime), len('\x01'*rateList[1]*playTime), len('\x01'*rateList[2]*playTime), len('\x01'*rateList[3]*playTime), len('\x01'*rateList[4]*playTime)]
# 
downloadDoneList = []    
downloadDonePendList = []


bufferLength = 0;
nowFragID = 0;

maxFragNum = 6
nowBlock = 0
blockList = []

qmin = 20
qmax = 50
qlimit = 60
sleepTime = 40
cut = 8
kP = 0.4
kD = 0.8
maxTime = 3600 * 0.5

slist = None

fig1 = None
fig2 = None

timelineData = []
bufferLengthData = []
rateData = []
rateTimelineData = []
rateVsTimeVsBufferData = []

allStartTime = 0
initTime = 0

unchangedBlock = 0
fragmentID = 0

class Server():
    def __init__(self, id, name):
        self.id = id
        self.bw = 0
        self.name = name
        self.downloadFrag = []
        self.downloadBlock = []
        self.downloadedFrag = []
        self.numofrequest = 0
        self.doneList = []
        self.downDur = 0
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
    def getavabw(self):
        global cut
        s = 0
        c = 0
        if(len(self.doneList)>=cut):
            for i in range(len(self.doneList)-cut, len(self.doneList)):
                s = s + self.doneList[i].downBw
                c = c + 1
        else:
            for i in range(0, len(self.doneList)):
                s = s + self.doneList[i].downBw
                c = c + 1
        if(c>0):
            return s / c
        else:
            return self.getBandwidth()

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
                    if(self.list[j].getavabw() < self.list[j+1].getavabw()):
                        temp = self.list[j]
                        self.list[j] = self.list[j+1]
                        self.list[j+1] = temp
        #for i in range(0,leng):
        #    print i,'->',self.list[i].name,'->',self.list[i].bw
    def getAvBw(self):
        t = 0
        c = 0
        for s in self.list:
            t = t + s.getavabw()
            c = c + 1
        return t / c
    def reinitdowndur(self):
        for s in self.list:
            s.downDur = 0



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
        cmin = serverlist.list[self.serverSize-1].getavabw()
        while True:
            serverlist.list[-1].numofrequest = 1
            self.fragNum = 1
            for i in range (0,self.serverSize-1):
                ci = serverlist.getServer(i).getavabw()
                serverlist.getServer(i).numofrequest = int(self.myFloor(ci,cmin))
                #print i,serverlist.getServer(i).numofrequest
                self.fragNum = self.fragNum + serverlist.getServer(i).numofrequest
            if(self.fragNum>maxFragNum):
                self.serverSize = self.serverSize - 1
                cmin = serverlist.list[self.serverSize-1].getavabw()
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
                jlist[j] = 1 / self.servers.getServer(j).getavabw()
                for t in range(0,i) :
                    jlist[j] += x[j][t] * (1 / self.servers.getServer(j).getavabw());
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
        if(t-x>0.7):
            x = x + 1
        return x
    def getalphan(self, n):
        ret= 0
        p = 0
        q = 0
        f = self.fragList[n]
        for i in range(0, self.serverSize):
            #q = q + self.getX(i, n) * f.downBw
            q = q + self.getX(i,n) * f.downByBw
            #print 'f.downByBw',f.downByBw
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
                if(rate - rateList[i] >= rateList[i]*0.05):
                    temp = rateList[i]
                    ret = i
        return ret

    def getNewRate(self):
        global blockList, qmin, qmax, kD, kP
        #pRate = rateList[self.rate-1]
        pRate = self.servers.getAvBw()
        newSelect = 0
        if(len(blockList)>=2):
            lastBlock = blockList[-2]
            if(self.endBuffer >= qmax or self.endBuffer <= qmin):
                vk = [0 for col in range(self.fragNum)]
                vk2 = [0 for col in range(self.fragNum)]
                vk3 = [0 for col in range(self.fragNum)]
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
                    # print f.id,alphaN,q_fragtEnk,q_blockSk,q_blockEk,fragDownDur,(q_blockEk - q0),((q_fragtEnk - q_blockSk) / (fragDownDur)),((1/(self.playtime*alphaN)) * kP * (q_blockEk - q0)),((1/(self.playtime*alphaN)) * kD * ((q_fragtEnk - q_blockSk) / (fragDownDur)))
                    # print ((1/(self.playtime*alphaN)) * kP * (q_blockEk - q0)),((1/(self.playtime*alphaN)) * 0.3 * (q_blockEk - q0)),((1/(self.playtime*alphaN)) * 0.2 * (q_blockEk - q0))
                    # print ((1/(self.playtime*alphaN)) * kD * ((q_fragtEnk - q_blockSk) / (fragDownDur))),((1/(self.playtime*alphaN)) * kD * ((q_fragtEnk - q_blockSk) / (fragDownDur))),((1/(self.playtime*alphaN)) * kD * ((q_fragtEnk - q_blockSk) / (fragDownDur)))
                    vk[i] = ((1/(self.playtime*alphaN)) * kP * (q_blockEk - q0))+ ((1/(self.playtime*alphaN)) * kD * ((q_fragtEnk - q_blockSk) / (fragDownDur)));
                    vk2[i] = ((1/(self.playtime*alphaN)) * 0.2 * (q_blockEk - q0))+ ((1/(self.playtime*alphaN)) * kD * ((q_fragtEnk - q_blockSk) / (fragDownDur)));
                    vk3[i] = ((1/(self.playtime*alphaN)) * 0.15 * (q_blockEk - q0))+ ((1/(self.playtime*alphaN)) * kD * ((q_fragtEnk - q_blockSk) / (fragDownDur)));
                if(self.endBuffer <= qmin):
                    vtemp = min(min(vk),min(vk2),min(vk3))
                    print 'min',min(vk),min(vk2),min(vk3),vtemp
                elif(self.endBuffer >= qmax):
                    vtemp = max(max(vk),max(vk2),max(vk3))
                    print 'max',max(vk),max(vk2),max(vk3),vtemp

                newRate = pRate + vtemp
                print 'pRate=',pRate,'vtemp =',vtemp, 'newRate =',newRate
                newSelect = self.getNewRateID(newRate) + 1
                if(self.endBuffer<=qmin and newSelect>self.rate):
                    newSelect = self.rate;
                elif(self.endBuffer>=qmax and newSelect<self.rate):
                    newSelect = self.rate;
                return newSelect
        return self.rate




class Fragment():
    def __init__(self, id, rate, playtime, block):
        global fragmentID
        self.id = id
        self.fragID = fragmentID
        fragmentID = fragmentID + 1
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
        self.downByBw = 0;
        self.downTotalDur = 0;
    def setDownloadBy(self, server):
        self.downBy = server
    def setDownloadDone(self):
        self.isDone = True
        self.block.downDoneSeq.append(self)
        self.downBy.doneList.append(self)
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
        global timelineData, bufferLengthData, rateData, fig1, fig2, allStartTime, rateTimelineData, unchangedBlock, maxTime, qlimit, sleepTime, initTime
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
                    b.startTime = time()
                    b.startBuffer = bufferLength
                    timelineData.append(time() - allStartTime)
                    bufferLengthData.append(bufferLength)
                    rateTimelineData.append(time() - allStartTime)
                    rateData.append(rateList[0])
                    blockList.append(b)
                    print 'block',nowBlock,' -> ',b.fragNum
                    nowBlock = nowBlock + 1
            elif(time() - allStartTime < maxTime):
                myBlock = blockList[-1]
                if(myBlock != None and myBlock.isDone==True):
                    myBlock.endTime = time()
                    #print frag & compute buffer
                    myBufferLength = myBlock.startBuffer
                    nowProcee = 0
                    print 'Server','\t','FragID','\t','Rate','\t\t','Down Dur','\t\t','Bandwidth','\t\t','BufferLength'
                    nowtime = 0
                    while nowProcee<myBlock.fragNum:
                        nowpro = 0
                        for fra in myBlock.downDoneSeq:
                            # if(fra.id > nowProcee):
                            #     nowpro = nowpro + 5
                            if(fra.id==nowProcee and fra.downTotalDur>nowtime):
                                fra.endBuffer = myBufferLength + 5 - (fra.downDur - nowtime)
                                nowtime = fra.downTotalDur
                                myBufferLength = fra.endBuffer
                                nowProcee = nowProcee + 1 
                                print '%s\t%d\t%d\t\t%.3f\t\t\t%.3fKbit/s\t\t\t%.3f\t%d\t'%(fra.downBy.name,fra.id,fra.rateInt,fra.downDur,fra.downBw,fra.endBuffer,fra.endDownload)
                                #print fra.downBy.name,'\t',fra.id,'\t',fra.rateInt,'\t',fra.downDur,'\t',int(fra.downBw),'KB/s\t',fra.endBuffer
                                break
                            elif(fra.id==nowProcee and fra.downTotalDur<=nowtime):
                                fra.endBuffer = myBufferLength + 5
                                #nowtime = fra.downDur
                                myBufferLength = fra.endBuffer
                                nowProcee = nowProcee + 1 
                                print '%s\t%d\t%d\t\t%.3f\t\t\t%.3fKbit/s\t\t\t%.3f\t%d\t'%(fra.downBy.name,fra.id,fra.rateInt,fra.downDur,fra.downBw,fra.endBuffer,fra.endDownload)
                                break
                    for fra in myBlock.downDoneSeq:
                        if(rateData[-1]!=fra.rateInt):
                            rateData.append(rateData[-1])
                            rateTimelineData.append(fra.endDownload - allStartTime)
                        timelineData.append(fra.endDownload - allStartTime)
                        bufferLengthData.append(fra.endBuffer)
                        rateTimelineData.append(fra.endDownload - allStartTime)
                        rateData.append(fra.rateInt)
                        rateVsTimeVsBufferData.append([fra.endDownload,fra.rateInt,fra.endBuffer,fra.fragID])
                    bufferLength = myBlock.fragList[-1].endBuffer
                    #start init new block
                    myBlock.endBuffer = bufferLength
                    
                    # elif(bufferLength<=qmin and newSelect == myBlock.rate):
                    #     unchangedBlock = unchangedBlock + 1
                    #     if(unchangedBlock >= 2 and newSelect<len(rateList) and newSelect>1):
                    #         newSelect = newSelect - 1
                    #         unchangedBlock = 0
                    #print 'getNew Select',newSelect
                    if(bufferLength > qlimit):
                        dif = bufferLength - sleepTime
                        bufferLength = bufferLength - dif
                        print 'in idle time...'
                        sleep(dif)
                        print 'idle done...'
                    slist.resort()
                    newSelect = myBlock.getNewRate()
                    # force rate change!
                    if(bufferLength>=qmax and newSelect == myBlock.rate):
                        unchangedBlock = unchangedBlock + 1
                        if(unchangedBlock >= 2 and newSelect<len(rateList)):
                            newSelect = newSelect + 1
                            unchangedBlock = 0
                    slist.reinitdowndur()
                    b = Block(nowBlock, slist, newSelect, 5)
                    b.startTime = time()
                    b.startBuffer = bufferLength
                    blockList.append(b)
                    print 'block',nowBlock,' -> ',b.fragNum,'timeDiff =',(b.startTime - initTime)
                    nowBlock = nowBlock + 1
            elif(fig1==None):
                ratel = [item[1] for item in rateVsTimeVsBufferData]
                timel = [item[0] for item in rateVsTimeVsBufferData]
                bufferl = [item[2] for item in rateVsTimeVsBufferData]
                id1 = [item[3] for item in rateVsTimeVsBufferData]

                fig1 = plt.subplot(411)
                fig1.plot(timel, bufferl)
                # print rateData
                # print timelineData
                fig2 = plt.subplot(412)
                fig2.plot(timel,ratel)

                fig2 = plt.subplot(413)
                fig2.plot(id1,ratel)
                for i in range(0,len(ratel)):
                    print '%d\t%d\t%.5f\t%.3f'%(id1[i],ratel[i],timel[i],bufferl[i])
                print '####################################'
                fig2 = plt.subplot(414)
                for s in slist.list:
                    frag1 = []
                    bw1 = []
                    for ff in s.downloadedFrag:
                        print '%d\t%d\t%.3f' % (s.id,ff.fragID,ff.downBw)
                        frag1.append(ff.endDownload)
                        bw1.append(ff.downBw)
                    print '####################################'
                    fig2.plot(frag1,bw1)
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
        begin=time()
        start= time()
        dur = 0
        so = "SEND" + "%d" % rate
        self.conn.send(so)
        while 1:
            #if total_data and time()-begin > timeout:
            #    break
            #elif time()-begin > timeout*2:
            #    break
            if recvLen>=dataPacket[rate-1]:
                break
            try:
                #while recvLen<dataPacket[rate-1]:
                data = self.conn.recv(dataPacket[rate-1])
                if len(data)>0:
                    total_data.append(data)
                    recvLen = recvLen + len(data)
                    begin = time()
                else:
                    self.conn.send(so)
                #else:
                #    time.sleep(0.01)
            except:
                pass
                #break
        #print 'length =' , recvLen,', time =' , dur, 'bw =' , recvLen/8/dur
        dur = time() - start
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
        global slist, blockList
        rate = 1
        #test speed
        #while True:
        if(self.s.getBandwidth()==None or self.s.getBandwidth()==0):
            print 'Bandwidth Testing start',self.name
            self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.conn.connect((serverList[self.server][0], serverList[self.server][1]))
            #self.conn.setLimit(serverLimit[self.server])
            #rev, d = self.recv_timeout(1)
            rev, d = self.recv_timeout(rate)
            #print rev, d
            if(rev>0 and d>0):
                print 'BW Testing:',self.name,'=' , rev/1024/d * 8, 'Kbit/s','block = ',rev,'dur=',d
                self.s.bw = rev/1024/d
        nowFrag = self.s.getDownloadFragment();
        while True:
            if(nowFrag!=None):
                self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.conn.connect((serverList[self.server][0], serverList[self.server][1]))
                #self.conn.setLimit(serverLimit[self.server])
                nowFrag.startDownload = time()
                nowFrag.startBuffer = bufferLength
                rate = nowFrag.rate;
                rev, d = self.recv_timeout(rate)
                nowFrag.endDownload = time()
                if(rev>0 and d>0):
                    #bufferLength = bufferLength + 5 - d
                    #print self.name,nowFrag.id,nowFrag.rateInt,d,int(rev/1024/d),bufferLength
                    self.s.bw = rev/1024/d * 8
                    nowFrag.downBw = self.s.bw
                    nowFrag.downByBw = self.s.getavabw()
                    nowFrag.downDur = d
                    self.s.downDur = self.s.downDur + d
                    nowFrag.downTotalDur = self.s.downDur
                    nowFrag.setDownloadDone()
                    #nowFrag.endBuffer = bufferLength
                    self.s.setDownloaded(nowFrag)
                    self.downloaded.append(nowFrag)
            nowFrag = self.s.getDownloadFragment();
                    
class BWSetter(Thread):
    def __init__(self, sertask):
        global serverLimit
        Thread.__init__(self, name="BWSetter")
        self.sertask = sertask
        self.mystart = time()
        #self.que = [[[120,2],[700,0.5],[1200,2]],[[570,2],[770,0.5]],[[430,0.5],[900,0.7],[1500,0.5]]]
        self.timeset = [120,430,570,700,770,900,1200,1500]
        self.settime = [[0,2],[2,0.5],[1,2],[0,0.5],[1,0.5],[2,0.7],[0,2],[2,0.5]]
    def run(self):
        global serverLimit, bufferLength
        baseline = [62.5* 8 * 1024,125* 8 * 1024,187.5* 8 * 1024]
        while True:
            timeDiff = int(time() - self.mystart)
            if(timeDiff in self.timeset):
                print 'start set bw!'
                index = self.timeset.index(timeDiff)
                setdata = self.settime[index]
                serverLimit[setdata[0]] = baseline[setdata[0]] * setdata[1]
                t = self.sertask[setdata[0]]
                if(t.conn!=None and t.conn!=0):
                    t.conn.setLimit(serverLimit[setdata[0]])
            sleep(1)

def start(numT):
    global allStartTime, initTime
    allStartTime = time()
    initTime = time()
    threadname = [ "server_%d" % i for i in range(0, numT) ]
    tasks = []
    for i in range(0,numT):
        task = serverConnect( threadname[i], i, 1, 5 )
        #task.setDaemon( True )
        task.start()
        tasks.append( task )
    task = Buffer()
    task.start()
    #tasks.append( task )
    #task = BWSetter(tasks)
    #task.start()

if __name__ == '__main__':
    #plt.interactive(True)
    #patch()
    slist = ServerList()
    start(3)
