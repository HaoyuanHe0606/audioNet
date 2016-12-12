#!/usr/bin/env python
# -*- coding:utf-8 -*-

import socket
import numpy
import time
import glob
import os
from random import randint

from wavReader import readWav, parseName

from soxAlter import soxAlter
from backgroundAlter import bgnAlter

import Queue
import threading


# 读取数据，放入队列的的线程函数
def _enQueueData(dpath, alter, Q):
    flist = glob.glob(dpath) 
    outf = './tmp/' + str(os.getpid()) + '.wav'
    thrd = threading.currentThread()
    while getattr(thrd, 'running', True):
        f = flist[randint(0, len(flist) - 1)]
        label = parseName(f)
        if alter:
            soxAlter(f, outf)
            sps, data = readWav(outf)
            bgnAlter(data)
        else:
            sps, data = readWav(f)
        data = data[1:] - data[0:len(data) - 1] # Z 变换
        Q.put((label, data), True)

# 创建线程，返回线程和队列
def _dataThreadOn(dpath, alter=True, maxQ=128):
    Q = Queue.Queue(maxQ)
    thrd = threading.Thread(target=_enQueueData, args = (dpath, alter, Q))
    thrd.start()
    return thrd, Q

# 发送所有数据，阻塞模式
def _sendall(s, data):
    length = len(data)
    minimal = 512
    prog = 0
    prog += s.send(data[0:8])
    while prog < length:
        prog += s.send(data[8:len(data)])
    return None

# 主要函数，创建一个socket，向sock_addr发送数据，并且负责IO线程的管理
def startAlterShipping(sock_addr='../data.sock', glob_string='/home/saturn/ds/data2/bluetooth/train/wav/*.wav'):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(sock_addr)

    thrd, Q = _dataThreadOn(glob_string, alter=True, maxQ=4)
    
    try:
        while True :
            label, data = Q.get()
            label = numpy.array([label, data.shape[0]], dtype=numpy.uint32)
            e = _sendall(s, label.tostring() + data.tostring())
            Q.task_done()
    except:
        print 'Out'
        s.close()
        thrd.running = False
        _, _ = Q.get()
        Q.task_done()
        threading.Thread.join(thrd)

if __name__ == '__main__':
    startAlterShipping()