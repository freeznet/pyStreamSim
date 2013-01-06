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

rateList = [300,700,1500,2500,3500]
playTime = 5

dataPacket = [playTime*col for col in rateList]

initSpeed = [500.0, 1000.0, 1500.0]
# speedSetting1 = [[850,860,3],[1120,1130,2],[1580,1590,3]]
# speedSetting2 = [[170,200,3],[620,640,0.5],[1293,1353,0.6]]
# speedSetting3 = [[500,520,0.3],[1050,1060,0.3],[1110,1120,0.247]]

speedSetting1 = [[500,510,3],[850,860,3],[1580,1590,3]]
speedSetting2 = [[170,180,3],[640,650,0.5],[1300,1310,0.5]]
speedSetting3 = [[400,410,0.3],[1050,1060,0.3],[1150,1160,0.3]]

# speedSetting1 = [[740,750,2]]#,[520,530,2.3]
# speedSetting2 = [[200,230,3],[600,630,0.5]]#,[555,577,1.5]
# speedSetting3 = [[440,470,0.3]]#,[561,572,0.9]
# speedSetting1 = [[15,23,0.5],[57,66,0.9],[85,92,1.5],[510,514,2.0],[635,641,0.7]]
# speedSetting2 = [[15,23,0.5],[57,66,0.9],[85,92,1.5],[510,514,2.0],[635,641,0.7]]
# speedSetting3 = [[15,23,0.5],[57,66,0.9],[85,92,1.5],[510,514,2.0],[635,641,0.7]]

speedSettings = [speedSetting1,speedSetting2,speedSetting3]

qmin = 15
qmax = 50
qlimit = 55
sleepTime = 30
kP = 1.1
kD = 0.8
maxTime = 2000

initTime = 0
allStartTime = 0
allStartBuffer = 0

maxFragNum = 9

serverList = None

nowBlock = 0
blockList = []

timelineData = []
bufferLengthData = []
rateData = []
rateTimelineData = []
ratevsbufferData = []
fragIntData = []
fragVsTimeData = []
rateVsTimeVsBufferData = []

FragNum = 0
fragList = []



class Server(object):
    def __init__(self, id, bw, speedset):
        self.id = id
        self.bw = bw
        self.downList = []
        self.doneList = []
        self.blockStartTime = 0
        self.nowTime = 0
        self.numofrequest = 0
        self.speedset = speedset
        self.totalDownDur = 0
        self.durRecord = 0
        self.rate = 1
    def isDone(self):
        return len(self.downList)==0
    def setbw(self, bw):
        self.bw = bw
    def getbw(self):
        for l in self.speedset:
            if(self.nowTime>=l[0] and self.nowTime<=l[1]):
                return self.bw * l[2]
        return self.bw
    def getavabw(self):
        cut = 16
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
            return self.getbw()
        
    def assignFrag(self, f):
        if(f not in self.downList):
            self.downList.append(f)
    def down(self):
        global allStartTime
        startTime = 0
        if(allStartTime < self.totalDownDur):
            allStartTime = self.totalDownDur
        self.nowTime = self.totalDownDur
        #self.totalDownDur = 0
        self.durRecord = 0
        while len(self.downList)>0:
            nowFrag = self.downList[0]
            rate = nowFrag.rate
            size = dataPacket[rate-1]
            nowFrag.startDownload = self.nowTime
            downDur = 0
            downBW = 0
            while size>0:
                sceBw = self.getbw()
                timediff = self.nowTime - int(self.nowTime)
                if(timediff<1 and timediff>0):
                    size = size - sceBw * (1 - timediff)
                    self.nowTime = int(self.nowTime + (1 - timediff))
                    downDur = downDur + (1 - timediff)
                    downBW = downBW + sceBw * (1 - timediff)
                else:
                    if(size>sceBw):
                        size = size - sceBw
                        self.nowTime = self.nowTime + 1
                        downDur = downDur + 1
                        downBW = downBW + sceBw
                    elif(size<=sceBw):
                        time = size / sceBw
                        downBW = downBW + size
                        self.nowTime = self.nowTime + time
                        downDur = downDur + time
                        size = 0
                        
            nowFrag.endDownload = self.nowTime
            nowFrag.downDur = downDur
            self.totalDownDur = self.totalDownDur + downDur
            downBW = downBW / downDur
            nowFrag.downBw = downBW
            nowFrag.setDownloadDone()
            #frag down dur done, remove from list
            #print '%d %d %d %.5f %f %.3f'%(self.id,nowFrag.id,nowFrag.rateInt,nowFrag.downBw,nowFrag.downDur,nowFrag.endDownload)
            self.downList.remove(nowFrag)
            self.doneList.append(nowFrag)

class ServerList(object):
    def __init__(self):
        self.list = []
    def add(self, s):
        if(s not in self.list):
            self.list.append(s)
    def get(self, i):
        return self.list[i]
    def getTotalBw(self):
        ret = 0.0
        for s in self.list:
            if(len(s.doneList)>0):
                ret = ret + s.doneList[-1].downBw
        return ret
    def getNewRate(self):
        global rateList
        rate = self.getTotalBw()
        ret = 0
        temp = rateList[0]
        for i in range(0,len(rateList)):
            if(rateList[i]<=rate):
                temp = rateList[i]
                ret = i
        return ret + 1
    def getDoneTime(self):
        t = []
        for s in self.list:
            t.append(s.totalDownDur)
        return min(t)
    def resort(self):
        if(self.list[0] != None and len(self.list)>1):
            leng = len(self.list)
            for i in xrange(leng):
                for j in xrange(leng - 1 - i):
                    if(self.list[j].getavabw() < self.list[j+1].getavabw()):
                        temp = self.list[j]
                        self.list[j] = self.list[j+1]
                        self.list[j+1] = temp
        # for i in range(0,leng):
        #    print i,'->',self.list[i].id,'->',self.list[i].bw
class Fragment(object):
    def __init__(self, id, rate, playtime, server):
        self.id = id
        self.rate = rate
        self.rateInt = rateList[rate-1]
        self.playtime = playtime
        self.startDownload = 0
        self.endDownload = 0
        self.startBuffer = 0
        self.endBuffer = 0
        self.downDur = 0
        self.downBy = None
        self.isDone = False
        self.downBw = server
    def setDownloadBy(self, server):
        self.downBy = server
        server.downList.append(self)
    def setDownloadDone(self):
        self.isDone = True
        # self.block.downDoneSeq.append(self)
        # allDone = True
        # for f in self.block.fragList:
        #     if(f.isDone==False):
        #         allDone = False
        # self.block.isDone = allDone

class Block(object):
    def __init__(self, id, serverlist, rate, playtime):
        global maxFragNum
        self.id = id
        self.servers = serverlist
        self.serverSize = len(serverlist.list)
        self.fragList = []
        self.sortList = []
        self.fragNum = 0
        self.rate = rate
        self.playtime = playtime
        self.isDone = False
        self.startTime = 0
        self.endTime = 0
        self.startBuffer = 0
        self.endBuffer = 0
        self.downDoneSeq = []
        #cmin = serverlist.list[self.serverSize-1].getbw()
        cmin = serverlist.list[self.serverSize-1].getavabw()
        #print 'cmin=',cmin
        while True:
            serverlist.list[-1].numofrequest = 1
            self.fragNum = 1
            for i in range (0,self.serverSize-1):
                #ci = serverlist.get(i).getbw()
                ci = serverlist.get(i).getavabw()
                serverlist.get(i).numofrequest = int(self.myFloor(ci,cmin))
                #print i,serverlist.get(i).id,serverlist.get(i).numofrequest
                self.fragNum = self.fragNum + serverlist.get(i).numofrequest
            if(self.fragNum>maxFragNum):
                self.serverSize = self.serverSize - 1
                #cmin = serverlist.list[self.serverSize-1].getbw()
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
        #print x
        for i in range(0,Nk):
            jstar = 0
            jlist = [0.0 for col in range(Smax)]
            for j in range(0, Smax):
                #jlist[j] = 1 / self.servers.get(j).getbw()
                jlist[j] = 1 / self.servers.get(j).getavabw()
                #print jlist
                for t in range(0,i) :
                    #jlist[j] += x[j][t] * (1 / self.servers.get(j).getbw());
                    jlist[j] += x[j][t] * (1 / self.servers.get(j).getavabw());
            jstar = jlist.index(min(jlist))
            #print 'jstar=',jstar,'i=',i
            x[jstar][i] = 1
            f = self.fragList[i]
            if(f != None):
                f.setDownloadBy(self.servers.get(jstar))
                self.servers.get(jstar).assignFrag(f)
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
        #print t,x
        if(t-x>0.7):
            x = x + 1
        return x
    def getalphan(self, n):
        ret= 0
        p = 0
        q = 0
        f = self.fragList[n]
        #print "f.downBw = ",n,f.downBw
        for i in range(0, self.serverSize):
            q = q + self.getX(i, n) * f.downBw
        for j in range(0, self.serverSize):
            t = self.getX(j, n)
            m = 0
            for i in range(0,n+1):
                m = m + self.getX(j, i)
            p = p + (t * m)
        #print p,q,self.serverSize
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
        global blockList, qmin, qmax, kP, kD
        pRate = rateList[self.rate-1]
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
                    #print f.id,alphaN,q_fragtEnk,q_blockSk,q_blockEk,fragDownDur
                    vk[i] = ((1/(self.playtime*alphaN)) * kP * (q_blockEk - q0))+ ((1/(self.playtime*alphaN)) * kD * ((q_fragtEnk - q_blockSk) / (fragDownDur)));
                if(self.endBuffer <= qmin):
                    #vtemp = min(min(vk),min(vk2),min(vk3))
                    vtemp = min(vk)
                elif(self.endBuffer >= qmax):
                    #vtemp = max(max(vk),max(vk2),max(vk3))
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

if __name__ == '__main__':
    sid = 0
    serverList = ServerList()
    nowTime = 0
    for spd in initSpeed:
        srv = Server(sid, spd, speedSettings[sid])
        serverList.add(srv)
        sid = sid + 1
    while allStartTime<2000:
        nowTime = serverList.getDoneTime()
        for s in serverList.list:
            if( s.totalDownDur <= nowTime):
                s.rate = serverList.getNewRate()
                f = Fragment(FragNum, s.rate, playTime, s)
                f.setDownloadBy(s)
                fragList.append(f)
                FragNum = FragNum + 1
                s.down()

    #compute buffer length
    limit = 0
    limitServer = -1
    timelimit = 0
    diff = 0
    for f in fragList:
        f.downBy.durRecord = f.downBy.durRecord + f.downDur
        if(f.downBy.durRecord > limit):
            allStartBuffer = allStartBuffer + playTime - (f.downBy.durRecord - limit)
            limit = f.downBy.durRecord
            f.endBuffer = allStartBuffer
            f.endDownload = f.endDownload + diff
            diff = 0
        else:
            allStartBuffer = allStartBuffer + playTime
            f.endBuffer = allStartBuffer
            f.endDownload = f.endDownload + diff
            diff = 0

        if(allStartBuffer > qlimit):
            diff = allStartBuffer - sleepTime
            allStartBuffer = allStartBuffer - diff

        # if(timelimit<=f.endDownload):
        #     timelimit = f.endDownload
        # else:
        #     f.endDownload = timelimit
        # if(len(rateData)>0 and rateData[-1]!=f.rateInt):
        #     rateData.append(rateData[-1])
        #     rateTimelineData.append(f.endDownload)
        # if(len(timelineData)>0 and timelineData[-1]==f.endDownload):
        #     #timelineData.append(f.endDownload)
        #     bufferLengthData[-1]=f.endBuffer
        #     ratevsbufferData[-1]=f.rateInt
        # else:
        timelineData.append(f.endDownload)
        bufferLengthData.append(f.endBuffer)
        ratevsbufferData.append(f.rateInt)
        rateTimelineData.append(f.endDownload)
        rateData.append(f.rateInt)
        fragIntData.append(f.id)
        fragVsTimeData.append(f.endDownload)
        rateVsTimeVsBufferData.append([f.endDownload,f.rateInt,f.endBuffer])
        print '%d\t\t%d\t\t%d\t\t%.3f\t\t\t%.3fKbit/s\t\t\t%.3f\t%.3f\t%.3f\t'%(f.downBy.id,f.id,f.rateInt,f.downDur,f.downBw,f.endBuffer,f.endDownload,f.downBy.durRecord)
    
    rateVsTimeVsBufferData.sort(key=lambda x: x[0])
    ratel = [item[1] for item in rateVsTimeVsBufferData]
    timel = [item[0] for item in rateVsTimeVsBufferData]
    bufferl = [item[2] for item in rateVsTimeVsBufferData]

    fig1 = plt.subplot(311)
    fig1.plot(timel, bufferl)
    fig2 = plt.subplot(312)
    fig2.plot(timel, ratel)
    # print rateData
    # print timelineData
    fig3 = plt.subplot(313)
    fig3.plot(fragIntData,fragVsTimeData)
    #fig3 = plt.subplot(213)
    #fig3.plot(fragIntData,fragVsTimeData)
    # for i in range(0,len(timelineData)):
    #     print '%.5f %d %.3f'%(timelineData[i],ratevsbufferData[i],bufferLengthData[i])
    plt.show()

    

#todo 
# main function
# frag download
# buffer length compute
# buffer setting