#!/usr/bin/python
#encoding=utf-8

import socket
import struct

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#第一个参数AF_INET，AF_INET6,AF_UNIX默认AF_INET,第二个参数有SOCK_STREAM和SOCK_DGRAM
#默认为SOCK_STREAM流套接字提供双向有序且不重复的数据服务也可以直接写s=socket.socket()

#host = socket.gethostname()
host = ''
port = 1234
print 'start linten'

rateList = [300,700,1500,2500,3500]
playTime = 5

dataPacket = ['\x01'*rateList[0]*playTime, '\x01'*rateList[1]*playTime, '\x01'*rateList[2]*playTime, '\x01'*rateList[3]*playTime, '\x01'*rateList[4]*playTime]



s.bind((host, port)) #绑定socket地址只有一个参数 是一个地址+端口的元组

s.listen(10) #开始监听，参数是队列长度

while True:
    c, addr = s.accept() #接受一个连接

    dataRev = c.recv(256)
    if(dataRev == 'CLOSE'):
    	c.close()
    if(dataRev == 'SEND1'):
    	print 'Send',rateList[0],'kbps data to',addr[0]
    	c.send(dataPacket[0])
    if(dataRev == 'SEND2'):
    	print 'Send',rateList[1],'kbps data to',addr[0]
    	c.send(dataPacket[1])
    if(dataRev == 'SEND3'):
    	print 'Send',rateList[2],'kbps data to',addr[0]
    	c.send(dataPacket[2])
    if(dataRev == 'SEND4'):
    	print 'Send',rateList[3],'kbps data to',addr[0]
    	c.send(dataPacket[3])
    if(dataRev == 'SEND5'):
    	print 'Send',rateList[4],'kbps data to',addr[0]
    	c.send(dataPacket[4])
    c.close()
