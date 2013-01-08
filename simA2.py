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

#short-term final
# speedSetting1 = [[400,410,3],[850,860,3],[1580,1590,3]]
# speedSetting2 = [[170,180,3],[640,650,0.5],[1300,1310,0.5]]
# speedSetting3 = [[510,520,0.3],[1050,1060,0.3],[1210,1220,0.3]]

#long-term final
speedSetting1 = [[800,1300,2],[1600,1800,2]]
speedSetting2 = [[200,750,2],[1100,1500,0.6]]
speedSetting3 = [[400,730,0.6],[1200,1500,0.4]]


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
idData = []

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
        self.diff = 0
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
        cut = 1
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
    timesleep = 0
    for f in fragList:
        f.downBy.durRecord = f.downBy.durRecord + f.downDur
        if(f.downBy.durRecord > limit):
            allStartBuffer = allStartBuffer + playTime - (f.downBy.durRecord - limit)
            limit = f.downBy.durRecord
            f.endBuffer = allStartBuffer
            f.startDownload = f.startDownload + timesleep
            f.endDownload = f.endDownload + timesleep
            # f.endDownload = f.endDownload + diff
            # diff = 0
        else:
            allStartBuffer = allStartBuffer + playTime
            f.endBuffer = allStartBuffer
            f.startDownload = f.startDownload + timesleep
            f.endDownload = f.endDownload + timesleep
            # f.endDownload = f.endDownload + diff
            # diff = 0

        if(allStartBuffer > qlimit):
            diff = allStartBuffer - sleepTime
            timesleep = timesleep + diff
            allStartBuffer = allStartBuffer - diff
            print 'sleep',diff,'at',f.endDownload,'timesleep=',timesleep
            for s in serverList.list:
                s.totalDownDur = s.totalDownDur + diff
            diff = 0

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
        idData.append(f.id)
        rateVsTimeVsBufferData.append([f.endDownload,f.rateInt,f.endBuffer,f.id])
        #print '%d\t\t%d\t\t%d\t\t%.3f\t\t\t%.3fKbit/s\t\t\t%.3f\t%.3f\t%.3f\t'%(f.downBy.id,f.id,f.rateInt,f.downDur,f.downBw,f.endBuffer,f.endDownload,f.downBy.durRecord)
        #id, rate, time, buffer
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
    #fig3.plot(fragIntData,fragVsTimeData)
    fig3.plot(idData, rateData)

    rateVsTimeVsBufferData.sort(key=lambda x: x[3])
    rate2 = [item[1] for item in rateVsTimeVsBufferData]
    id2 = [item[3] for item in rateVsTimeVsBufferData]

    # for f in serverList.get(0).doneList:
    #     print '%d\t\t%d\t\t%d\t\t%.3f\t\t\t%.3fKbit/s\t\t\t%.3f\t%.3f\t%.3f\t'%(f.downBy.id,f.id,f.rateInt,f.downDur,f.downBw,f.endBuffer,f.endDownload,f.downBy.durRecord)
    # print '#####################################'
    # for f in serverList.get(1).doneList:
    #     print '%d\t\t%d\t\t%d\t\t%.3f\t\t\t%.3fKbit/s\t\t\t%.3f\t%.3f\t%.3f\t'%(f.downBy.id,f.id,f.rateInt,f.downDur,f.downBw,f.endBuffer,f.endDownload,f.downBy.durRecord)
    # print '#####################################'
    # for f in serverList.get(2).doneList:
    #     print '%d\t\t%d\t\t%d\t\t%.3f\t\t\t%.3fKbit/s\t\t\t%.3f\t%.3f\t%.3f\t'%(f.downBy.id,f.id,f.rateInt,f.downDur,f.downBw,f.endBuffer,f.endDownload,f.downBy.durRecord)
    # suma = len(fragList)
    # print suma
    #fig3 = plt.subplot(213)
    #fig3.plot(fragIntData,fragVsTimeData)
    for i in range(0,len(timel)):
        print '%d %d %.5f %.3f'%(id2[i],rate2[i],timel[i],bufferl[i])
    plt.show()

    

#todo 
# main function
# frag download
# buffer length compute
# buffer setting