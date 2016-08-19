#coding:utf-8
# This script is used to get the following parameters FROM CLENT:
# Time Stamp
# GPS location(latitude,longitude)
# moving speed
# signal_power_dbm
# noise_power_dbm
# mother_board_temp_sensor2
# daughter_card_temp_sensor
# channel
# downlink_modulation
# PER


#Those information will coma-separated and writen to the file named: Client_sysinfor_data.cvs
# in the current working directory
# Originated on August 17, 2016

import serial
import socket
import signal
import os
import subprocess
import time

readPort = raw_input("Which port GPS Module will use:\n")
POLL_INTERVAL = float(raw_input("Reading Cycle in Second:\n"))   
HOST =raw_input("What is the ip address of client(169.254.0.9)\n")     
BUFFER_SIZE = 65535
readSpeed = 115200

 ##indicate the type of sentence
stableSen = "$GPGSA" 
locationSen = "$GPRMC"
speedSen = "$GPVTG"

PORT = 32921

Aowa_RPC_GetSystemInfo_NUM = 117
Aowa_Remote_GetAgentULSInfoSimple_NUM = 69
Aowa_RPC_GetLastRAInfo = 60
Aowa_RPC_EnumAgents = 35

mmac = 'bc:6a:29:d8:41:17'
s = None
line = ""
data_file_name = "Client_sysinfo_data.txt"


gModTable = ['QPSK','16QAM','64QAM','']
gPuncTable = ['1/2','2/3','3/4','5/6','']

# usage report function start
def getReadableTime():
    #return strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime())
    return time.strftime("%a. %d %b %Y %H:%M:%S +0000", time.localtime())

def socket_init(host, port):
    # create a TCP/IP socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print 'socket created'
    except socket.error as msg:
        print 'socket cannot be created. C' 
        s = None
        pass

    # connect the socket to the port where the server (remote host) is listening
    try:
        server_address = (host, port)
        print 'connecting to: ',  server_address
        s.connect(server_address)
    except socket.error as msg:
        print 'Failed to connecting socket. '
        s.close()
        s = None
        pass

    if s is None:
        print >> sys.stderr,  'could not open socket'
        sys.exit(1)

    return s

def socket_uninit(s):
    print 'closing socket'
    s.close()
    
def AowaPingPongCmd(s, cmd, inMac):
    MESSAGE = "<RPCV1>" + str(cmd) + " " + inMac + "</RPCV1>\r\n"
    s.send(MESSAGE)
    
    data = s.recv(BUFFER_SIZE)

    # The first field is OK word, skip it
    # skip also the space, which comes the index 3
    r_data = data[3:] 
    return r_data 
    
def save_data(line):
    with open(data_file_name, "a") as myfile:
        line = '\n'+ getReadableTime() + ','+ line
        myfile.write(line)
        myfile.close()  
        
def formatLocation(information):
    #read the abs value
    latitude = float(information[3])
    longitude = float(information[5])
    
    #convert to degree value
    latitudeDegree = latitude//100
    latitude=(latitude-latitudeDegree*100)/60+latitudeDegree
    longitudeDegree = longitude//100
    longitude=(longitude-longitudeDegree*100)/60+longitudeDegree
    
    #put direction
    if information[4] == 'S':
        latitude *= -1
    if information[6] == 'W':
        longitude *= -1
    
    return str(latitude) + ',' + str(longitude)

    #this get location and speed.
def getLocation():
    ser = serial.Serial(readPort,readSpeed)  ##read sentence from device
    while 1:      ##keep reading until get a result could be return
        serial_line = ser.readline()
        information=serial_line.split(",")
        if information[0] == stableSen and (information[2] == '2' or information[2] == '3' or information[2] == '1'): ##if signal is strong enough
            lookingPosition = True
            lookingSpeed = True
            while lookingPosition or lookingSpeed:     ##looking for position sentece
                serial_line = ser.readline()
                information=serial_line.split(",")
                if information[0] == speedSen:
                    speedInfo = information[7]
                    lookingSpeed = False
                ##check position sentence and is active
                if information[0] == locationSen and information[2] == 'A': 
                    locationInfo = formatLocation(information)
                    lookingPosition = False
            
            return locationInfo + ',' + speedInfo
           
                
                    
                    
def signal_handler(signal, frame):
    global interrupted
    interrupted = True

    
def Get_parameters():
    global s
    global line
    global POLL_INTERVAL
    
    line = "Connection Drlopped"
    
    #get internet state
    result = subprocess.Popen("ping -w 1 8.8.8.8", shell=True, stdout=subprocess.PIPE).stdout.read()
    aa = result.split(',')
    
    recievePac = aa[1].split('=')[1]
    if int(recievePac) != 0:
        a = aa[4].split('=')
        latency = a[1]
    else:    
        latency = '-999'
           
    #get mac address
    macInfo = AowaPingPongCmd(s,Aowa_RPC_EnumAgents,'ff:ff:ff:ff:ff:ff')
    macData = macInfo.split()
    mmc = macData[1]
        
    #get system info
    sysInfo = AowaPingPongCmd(s,Aowa_RPC_GetSystemInfo_NUM,'ff:ff:ff:ff:ff:ff')  
    #check result, and save GPS info
    if len(sysInfo) > 1:
        #print sysInfo
        data = sysInfo.split()
    else:
        print "Faile in getting SystemInfo"
             
    #get modulation information and PER information
    modulationInfo = AowaPingPongCmd(s,Aowa_Remote_GetAgentULSInfoSimple_NUM,mmac)
    if len(modulationInfo) > 1:
        modulation_Data = modulationInfo.split()            
        #some time, the client give the number no meanning
        if int(modulation_Data[2]) > 2:
            modulation_Data[2] = 3
        if int(modulation_Data[3]) > 3:
            modulation_Data[3] = 4

        #use index find the phyMode
        phyMode_dl = gModTable[int(modulation_Data[2])] + ' ' + gPuncTable[int(modulation_Data[3])]  
        PER = round((float(modulation_Data[7])/float(modulation_Data[6])),3) 
                
    else:
        print 'no base linked.'
        
                    
    #get GPS location information
    location = getLocation()
            
    #put all information together
    line  = latency + ',' + location + ',' + data[31] + ',' + data[33] + ',' + data[41] + ',' + data[43] + ',' + data[115] + ','  + phyMode_dl +',' + str(PER) + '%' 
    save_data(line)
    print line
    time.sleep(POLL_INTERVAL)
        

        

def main():
    global HOST
    global PORT
    global s
    
    signal.signal(signal.SIGINT,signal_handler)
    interrupted = False
    s = socket_init(HOST, PORT)
    
    print(time.ctime())
    
    
    while True:
        Get_parameters()
        #break
        if interrupted:
            print'Stop Reading data.'
            break 
    socket_uninit(s)

if __name__ ==  '__main__':
    main()
    
    
    

