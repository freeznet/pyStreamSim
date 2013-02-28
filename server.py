#!/usr/bin/python
#encoding=utf-8

import socket,select
import struct
import random
import string

#s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

host = ''
port = 1234
print 'start linten'

rateList = [300,700,1500,2500,3500,7000]
playTime = 5

dataPacket = [rateList[0]*playTime*128, rateList[1]*playTime*128, rateList[2]*playTime*128, rateList[3]*playTime*128, rateList[4]*playTime*128, rateList[5]*playTime*128]

def main():
    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((host, port))
    s.listen(5)
    socklist=[s]
    while True:
        listening(socklist)

def listening(socklist):
   rlist,wlist,elist=select.select(socklist,[],[],0)
   for sock in rlist:
       if sock==socklist[0]:
            print 's.accept',socklist
            clientsock,clientaddr = sock.accept()
            socklist.append(clientsock)
       else:
            dataRev=sock.recv(256)
            #print [words]
            if(dataRev == 'CLOSE'):
                sock.close()
            if(dataRev == 'SEND1'):
                print 'Send',rateList[0],'kbps data'
                sock.send(random_bytes(dataPacket[0]))
            if(dataRev == 'SEND2'):
                print 'Send',rateList[1],'kbps data'
                sock.send(random_bytes(dataPacket[1]))
            if(dataRev == 'SEND3'):
                print 'Send',rateList[2],'kbps data'
                sock.send(random_bytes(dataPacket[2]))
            if(dataRev == 'SEND4'):
                print 'Send',rateList[3],'kbps data'
                sock.send(random_bytes(dataPacket[3]))
            if(dataRev == 'SEND5'):
                print 'Send',rateList[4],'kbps data'
                sock.send(random_bytes(dataPacket[4]))
            if(dataRev == 'SEND6'):
                print 'Send',rateList[5],'kbps data'
                sock.send(random_bytes(dataPacket[5]))
            #c.close()

def random_bytes(size):  
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(size))

if __name__ == "__main__":
   main()

