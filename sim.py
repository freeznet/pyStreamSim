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

dataPacket = [1500, 3500, 7500, 12500, 17500]

initSpeed = [500, 1000, 1500]

qmin = 10
qmax = 50
qlimit = 60

allStartTime = 0

class Server(object):
    def __init__(self, id, bw):
        self.id = id
        self.bw = bw
        self.downList = []
        self.doneList = []
        self.blockStartTime = 0
        self.nowTime = 0
        self.numofrequest = 0
    def setbw(self, bw):
        self.bw = bw
    def getbw(self):
        return self.bw
    def down(self):
        startTime = 0
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
                    downBW = downBW + sceBw
                else:
                    if(size>sceBw):
                        size = size - sceBw
                        self.nowTime = self.nowTime + 1
                        downDur = downDur + 1
                        downBW = downBW + sceBw
                    elif(size<=sceBw):
                        time = size / sceBw
                        size = 0
                        self.nowTime = self.nowTime + time
                        downDur = downDur + time
                        downBW = downBW + sceBw
            nowFrag.endDownload = self.nowTime
            nowFrag.downDur = downDur
            nowFrag.downBW = downBW
            nowFrag.setDownloadDone()
            #frag down dur done, remove from list
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
    def resort(self):
        if(self.list[0] != None and len(self.list)>1):
            leng = len(self.list)
            for i in xrange(leng):
                for j in xrange(leng - 1 - i):
                    if(self.list[j].getbw() < self.list[j+1].getbw()):
                        temp = self.list[j]
                        self.list[j] = self.list[j+1]
                        self.list[j+1] = temp
class Fragment(object):
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
        server.downList.append(self)
    def setDownloadDone(self):
        self.isDone = True
        self.block.downDoneSeq.append(self)
        allDone = True
        for f in self.block.fragList:
            if(f.isDone==False):
                allDone = False
        self.block.isDone = allDone

class Block(object):
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
        cmin = serverlist.list[self.serverSize-1].getbw()
        while True:
            serverlist.list[-1].numofrequest = 1
            self.fragNum = 1
            for i in range (0,self.serverSize-1):
                ci = serverlist.get(i).getbw()
                serverlist.get(i).numofrequest = int(self.myFloor(ci,cmin))
                #print i,serverlist.get(i).numofrequest
                self.fragNum = self.fragNum + serverlist.get(i).numofrequest
            if(self.fragNum>maxFragNum):
                self.serverSize = self.serverSize - 1
                cmin = serverlist.list[self.serverSize-1].getbw()
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
                jlist[j] = 1 / self.servers.get(j).getbw()
                for t in range(0,i) :
                    jlist[j] += x[j][t] * (1 / self.servers.get(j).getbw());
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
                    vk2[i] = ((1/(self.playtime*alphaN)) * 1.5 * (q_blockEk - q0))+ ((1/(self.playtime*alphaN)) * kD * ((q_fragtEnk - q_blockSk) / (fragDownDur)));
                    vk3[i] = ((1/(self.playtime*alphaN)) * kP*2 * (q_blockEk - q0))+ ((1/(self.playtime*alphaN)) * kD * ((q_fragtEnk - q_blockSk) / (fragDownDur)));
                if(self.endBuffer <= qmin):
                    vtemp = min(min(vk),min(vk2),min(vk3))
                    print 'min',min(vk),min(vk2),min(vk3),vtemp
                elif(self.endBuffer >= qmax):
                    vtemp = max(max(vk),max(vk2),max(vk3))
                    print 'max',max(vk),max(vk2),max(vk3),vtemp

                newRate = pRate + vtemp
                #print 'vtemp = ',vtemp, 'newRate = ',newRate
                newSelect = self.getNewRateID(newRate) + 1
                if(self.endBuffer<=qmin and newSelect>self.rate):
                    newSelect = self.rate;
                elif(self.endBuffer>=qmax and newSelect<self.rate):
                    newSelect = self.rate;
                return newSelect
        return self.rate

#todo 
# main function
# frag download
# buffer length compute
# buffer setting