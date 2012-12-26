#!/user/bin/env python
#-*- encoding:utf-8 -*-
import socket
import sys
import os
import time
import urllib
from threading import Thread


sockIndex = 1
serverList = [['42.121.78.93',1234],['106.186.17.248',1234],['127.0.0.1',1234]]

rateList = [300,700,1500,2500,3500,7000]
playTime = 5 * 128

dataPacket = [len('\x01'*rateList[0]*playTime), len('\x01'*rateList[1]*playTime), len('\x01'*rateList[2]*playTime), len('\x01'*rateList[3]*playTime), len('\x01'*rateList[4]*playTime), len('\x01'*rateList[5]*playTime)]
downloadDoneList = []
downloadDonePendList = []

bufferLength = 0;
nowFragID = 0;

class Server():
    def __init__(self, id, name):
        self.id = id
        self.bw = 0
        self.name = name
        self.downloadFrag = []
        self.downloadBlock = []
    def getBandwidth(self):
        return self.id
    def assignFrag(self, f):
        if(f not in self.downloadFrag):
            self.downloadFrag.append(f)
    def assignBlock(self, b):
        if(b not in self.downloadBlock):
            self.downloadBlock.append(b)

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

class Block():
    def __init__(self):
        return

class fragment():
    def __init__(self, id, rate):
        self.id = id
        self.rate = rateList[rate-1]
        self.playtime = 5
        self.startDownload = 0
        self.endDownload = 0
        self.startBuffer = 0
        self.endBuffer = 0
        self.downDur = 0

class serverConnect(Thread):
    def __init__(self, threadname, serverID,  rate, ptime):
        Thread.__init__(self, name=threadname)
        self.name = threadname
        self.nowRate = rate
        self.playTime = ptime
        self.downloaded = []
        self.server = serverID
        self.conn = 0

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
        rate = 1
        while True:
            self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.conn.connect((serverList[self.server][0], serverList[self.server][1]))
            nowFragID = nowFragID + 1
            tmpFrag = fragment(nowFragID,rate)
            tmpFrag.startDownload = time.time()
            tmpFrag.startBuffer = bufferLength
            rev, d = self.recv_timeout(rate)
            tmpFrag.endDownload = time.time()
            if(rev>0 and d>0):
                print self.name,'@',tmpFrag.id,'---> length =' , rev,', time =' , d, 'bw =' , rev/1024/d, 'KB/s'
                tmpFrag.downDur = d
                #computeBuffer(tmpFrag)
                self.downloaded.append(tmpFrag)
                rate = rate + 1
                if rate>6:
                    rate = 6





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
    threadname = [ "server_%d" % i for i in range(0, numT) ]
    tasks = []
    for i in range(0,numT):
        task = serverConnect( threadname[i], i, 1, 5 )
        #task.setDaemon( True )
        task.start()
        tasks.append( task )



if __name__ == '__main__':
    start(2)
