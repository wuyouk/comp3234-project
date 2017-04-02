#!/usr/bin/python3

# Student name and No.: Wu You - 3035086120
# Student name and No.: Zhu Youwei - 3035087198
# Development platform: Mac
# Python version: Python 3.5.0
# Version: 1


from tkinter import *
import sys
import socket
import time

import threading

#
# Global variables
#
gLock = threading.Lock()

NAMED = False
JOINED = False
CONNECTED_ROOM = False
quit_alert = False #Set to true if quit, otherwise false
sockfd = None
room = None # class Room
user = None # class Peer
ip = "localhost"
pass



#
# This is the hash function for generating a unique
# Hash ID for each peer.
# Source: http://www.cse.yorku.ca/~oz/hash.html
#
# Concatenate the peer's username, str(IP address), 
# and str(Port) to form the input to this hash function
#
def bubbleSort(alist):
    for passnum in range(len(alist)-1,0,-1):
        for i in range(passnum):
            if alist[i].hashid>alist[i+1].hashid:
                temp = alist[i]
                alist[i] = alist[i+1]
                alist[i+1] = temp

def sdbm_hash(instr):
    hash = 0
    for c in instr:
        hash = int(ord(c)) + (hash << 6) + (hash << 16) - hash
    return hash & 0xffffffffffffffff

# function to establish TCP connection, return a socket object sockfd
def tcp_connect(ip,port):
    try:
        sockfd = socket.socket()
        sockfd.connect((ip, int(port)))
    except socket.error as emsg:
        print("Socket connect error:", emsg)
        return False, emsg
        # sys.exit(1)
    return True, sockfd


# function to send and receive TCP messages
def send_request(sockfd, request):
    try:
        sockfd.send(request.encode('ascii'))
    except socket.error as emsg:
        print("E: Socket send error:", emsg)
        return False
    return True

def recv_message(sockfd, length):
    try:
        rmsg = sockfd.recv(length)
        rmsg = rmsg.decode("ascii")
    except socket.timeout:
        return True, "" # time out return true and empty msg
    except socket.error as emsg:
        print("E: Socket recv error:", emsg)
        return False, "" # broken connection
    if not rmsg:
        return False, rmsg 
    else:
        return True, rmsg

# Class for peer
class Peer:
    def __init__(self, name, ip, port, msgid):
        self.name = name
        self.ip = ip
        self.port = port
        self.msgid = [msgid]
        self.hashid = self.getHashId()
        self.sockfd = None
        self.isconnected = False
        self.isforward = False

    def getHashId(self, user = None):
        if user == None:
            string = str(self.name) + str(self.ip) + str(self.port)
        else:
            string = str(user.name) + str(user.ip) + str(user.port)
        return sdbm_hash(string)

    def disconnect(self):
        self.isconnected = False
        self.isforward = False
        self.sockfd.close()
        self.sockfd = None

    def forwardconnect(self):
        self.isconnected = True
        self.isforward = True

    def backwardconnect(self):
        self.isconnected = True
        self.isforward = False

#Class for room
class Room:
    def __init__(self, name="", ip="", port=None, peers=None,sockfd=None):
        self.name = name
        self.ip = ip
        self.port = port
        self.sockfd = sockfd
        self.hashid = 0
        self.peers_ths = [] # manage connection with peers threads
        self.keepalive_th = None # keepalive thread
        self.listen_th = None # listening to incoming request
        if peers == None:
            self.peers = []
        else:
            self.peers = peers

    def getForward(self):
        for peer in self.peers:
            if peer.isforward == True:
                return peer
        return None

    def hasForward(self):
        for peer in self.peers:
            if peer.isforward == True:
                return True
        return False

    def hasPeer(self,user):
        cur_id = 0
        if type(user) is not int:
            cur_id = user.hashid
        else:
            cur_id = user
        for peer in self.peers:
            if peer.hashid == cur_id:
                return True
        return False

    def getPeer(self, hashid):
        for peer in self.peers:
            if peer.hashid == hashid:
                return peer
        return None

    def addPeer(self, user):
        if not self.hasPeer(user):  
            self.peers.append(user)
            return True
        return False

    def delPeer(self, user):
        for peer in self.peers:
            if peer.hashid == user.hashid:
                self.peers.remove(peer)
                return True
        return False

    def updatePeer(self, new_room):
        for peer in self.peers: # delete inactive peer
            if not new_room.hasPeer(peer):
                self.delPeer(peer)
        for peer in new_room.peers: # add new peer
            if not self.hasPeer(peer):
                self.addPeer(peer)
        return

    def sendAll(self, message):
        for peer in self.peers:
            if peer.isconnected:
                status = send_request(peer.sockfd,message)
                if not status:
                    print("Connection broke")
                    peer.disconnect()
                else:
                    print(peer.port,"sent")

#
# Helper Functions 
#

# join request helper function
# function to send join request: J:roomname:username:userIP:userPort::\r\n
def j_req(user,room):
    request = "J:" + str(room.name) + ":" + str(user.name) + ":"\
                   + str(user.ip) + ":" + str(user.port)\
                   + "::\r\n"
    status = send_request(room.sockfd, request)
    return status

# function to get peers from join request's response:
# example: M:MSID:userA:ip:port return room contains tom's information
def j_res_parse(rmsg):
    msg = rmsg.split(":")
    peer_list = []
    i = 2 # M:MSID:userA user information start at index 2
    while (i < len(msg) - 2):
        try:
            cur = Peer(msg[i], msg[i + 1], int(msg[i + 2]),0)
        except ValueError:
            print ('Can not parse rmsg in choose_forward')
        peer_list.append(cur)
        i = i + 3
    # testing     
    # for peer in peer_list:
    #     print(peer.port)
    return Room(peers = peer_list)

# Peer request helper function
# send peer connection request
def p_req(sender, target, room):
    msg = "P:" + room.name + ":" + sender.name + ":" + sender.ip + ":" + \
    str(sender.port) + ":" + str(max(sender.msgid)) + "::\r\n"

    status = send_request(target.sockfd, msg)
    if status:
        s2, rmsg = recv_message(target.sockfd, 1000)
    return s2

# send peer connection response
def p_res(sender, target, room):
    msg = "S:" + max(sender.msgid) + "::\r\n"
    status = send_request(target.sockfd, msg)
    return status
# function to get peer from p request message:
def p_req_parse(rmsg,room):
    msg = rmsg.split(":")
    # check header and room information
    if msg[0] != "P" or msg[1] != room.name:
        return False, None
    # extract peer
    try:
        cur = Peer(msg[2], msg[3], int(msg[4]),int(msg[5]))
    except ValueError:
        print ('Can not parse rmsg in choose_forward')
    if room.hasPeer(cur):
        peer = room.getPeer(cur.hashid)
        peer.msgid = []
        peer.msgid.append(int(msg[5]))
        return True, peer
    else:
        return False, None

# Text message request helper function:
#send a message
#T:roomname:originHID:origin_username:msgID:msgLength:Message content::\r\n
def send_t(user, target, room, message):
    msg = "T:" + room.name + ":" + str(user.hashid) + ":" + user.name + \
    ":" + max(user.msgid) + ":" + len(message) + ":" + message + "::\r\n"
    status = send_request(target.sockfd, msg)
    return status
#pase message to get sender and message body
def parse_t(room, rmsg):
    msg = rmsg.split(":")
    try:
        hashid = int(msg[2])
        msgid = int(msg[4])
    except ValueError:
        print("Can not parse_t")
        return False, None, None, None
    if room.hasPeer(hashid):
        if msgid not in room.getPeer(hashid).msgid:
            # print("new message received")
            # if body has : splited, join back
            msg_body = msg[6]
            for piece in msg[7:len(msg)-2]:
                msg_body = msg_body + ":"
                msg_body = msg_body + piece
            return True, msg[3], msg_body, msgid, hashid
        # else:
        #   print("old message received")
    return False, None, None, None, None

# function to set up forward link
def choose_forward(rmsg):
    global room, user

    cur_room = j_res_parse(rmsg)
    room.updatePeer(cur_room)
    #2.sort the membership by increasing order
    bubbleSort(room.peers)
    #3.use H's hash id to find its index X in list
    myhashid = user.hashid
    start = 0
    for peer in room.peers:
        curhid = peer.hashid
        if curhid <= myhashid:
            start = start + 1
    #4.
    my_index = start - 1
    if start == len(room.peers):
        start = 0
    # print("Peer number:",len(room.peers))
    established = False
    while (start != my_index):
        peer = room.peers[start]
        if peer.isconnected:
            start = (start + 1) % len(room.peers)
        else: 
            # try to build forward link with this peer
            # print("Try:", peer.port)
            success , sockfd = tcp_connect(peer.ip,peer.port)
            if success:
                peer.sockfd = sockfd
                status = p_req(user, peer, room)
                if status:      
                    # add peer to forward link
                    peer.forwardconnect()
                    established = True
                    p_th = threading.Thread(target=peer_th, args=(peer,))
                    p_th.start()
                    room.peers_ths.append(p_th)
                    break
                else:
                    start = (start + 1) % len(room.peers)
            else:
                start = (start + 1) % len(room.peers)
    # testing
    # if established:
    #     print("link:" + str(user.port) + str(peer.port)) 
    # else:
    #     print("linkfailed")
    return established

# listening thread
def listen_th():
    print("listen_th running")
    global user, room, quit_alert
    sockfd = socket.socket()
    ## for testing: server won't occupy port after program terminate
    sockfd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sockfd.settimeout(1.0) # what happens after timeout -- zhuyouwei
    try:
        sockfd.bind(('', user.port))
    except socket.error as emsg:
        print("Socket bind error: ", emsg)
        
    # set socket listening queue
    sockfd.listen(10)
    # this is for keeping all incomming connections
    while True and not quit_alert:
        try:
            newfd, caddr = sockfd.accept()
            print("new connection")
        except socket.timeout:
            continue
        # peer to peer handshake
        should_add = False
        #parse received message of peer information
        status, rmsg = recv_message(newfd, 1000)
        if status and rmsg:
            #check if peer in the room
            in_room, peer = p_req_parse(rmsg, room)
            if in_room:
                #if peer in the room
                should_add = True
            else:
                #if peer is unknown, send join request to update room
                status = j_req(user, room)
                status, rmsg2 = recv_message(room.sockfd,1000)
                if status and rmsg2:
                    cur_room = j_res_parse(rmsg2)
                    room.updatePeer(cur_room)
                    #check if peer in the room again
                    in_room, peer = p_req_parse(rmsg, room)
                    if in_room:
                        should_add = True
        # if peer is unknown continue
        if not should_add:
            newfd.close()
            continue
        # otherwise send the hand shake message to this peer and add to queue
        peer.sockfd = newfd
        peer.backwardconnect()
        msg = "S:" + str(max(user.msgid)) + "::\r\n"
        send_request(newfd, msg)

        p_th = threading.Thread(target=peer_th, args=(peer,))
        p_th.start()
        # add this new thread to cthread list
        room.peers_ths.append(p_th)
    return

# thread to handle peer information
def peer_th(current):
    print("peer_th",current.port)
    global gLock, room, user, quit_alert
    sockfd = current.sockfd
    sockfd.settimeout(1.0)

    while True and not quit_alert:
        # wait for any message to arrive
        status, rmsg = recv_message(current.sockfd,1024)
        if status and not rmsg:
            continue # timeout occurs
        if status and rmsg:
            valid, name, body, msgid, hashid = parse_t(room, rmsg)
            if not valid:
                #update peer and check again
                status2 = j_req(user, room)
                status2, rmsg2 = recv_message(room.sockfd,1000)
                if status2 and rmsg2:
                    cur_room = j_res_parse(rmsg2)
                    room.updatePeer(cur_room)
                valid, name, body, msgid, hashid = parse_t(room, rmsg)
                if not valid:
                    continue
            room.getPeer(hashid).msgid.append(msgid)
            msg = name + ":" + body
            MsgWin.insert(1.0,"\n" + msg)
            for peer in room.peers:
                if peer.isconnected and peer.hashid != current.hashid:
                    success = send_request(peer.sockfd,rmsg)
                    if not success:
                        peer.disconnect()
            
        # else a broken connection is detected, do the following
        # use mutex lock gLock to protect the access of WList
        else:
            print("Peer Leave", current.port)
            if current.isforward == True: # find a new forward
                # send 'J' request to room server
                status = j_req(user,room)
                # receive response from room server
                status2, rmsg = recv_message(room.sockfd, 1000)
                if status and status2 and rmsg:
                    choose_forward(rmsg)

            current.disconnect()
            break
    return

# thread to keepalive by sending join requests
def keepalive_th(action):

    global JOINED, CONNECTED_ROOM, user, room, quit_alert
    
    while True and quit_alert:
        time.sleep(10)
        status = j_req(user, room)
        # check if socket.send is successful
        if not status:
            CmdWin.insert(1.0, "\n[Reject-" + action + "] " )   
        # receive response from room server
        status, rmsg = recv_message(room.sockfd, 1000)
        # check if successfully receive response from room server
        if rmsg:
            if rmsg[0] == "F":
                CmdWin.insert(1.0, "\n[Reject-" + action + "] " + rmsg)
            #parse the return message update the room
            cur_room = j_res_parse(rmsg)
            room.updatePeer(cur_room)
            #find new forwardlink if previous one break
            if not room.hasForward():
                choose_forward(rmsg)
            CmdWin.insert(1.0, "\n[" + action + "] " + rmsg)
            JOINED = True
        else:
            CmdWin.insert(1.0, "\n[Reject-" + action + "] broken connection with server")
            JOINED = False
            CONNECTED_ROOM = False
            break





def do_User():
    global JOINED, NAMED, user, ip
    # check if user input for username is empty
    if not userentry.get():
        CmdWin.insert(1.0, "\n[Reject-User] Username cannot be empty")
    else:
        # check if user has joined a chatroom group
        if JOINED:
            CmdWin.insert(1.0, "\n[Reject-User] You cannot change username after JOINED")
        else:
            # register username
            NAMED = True
            user = Peer(userentry.get(), ip, int(sys.argv[3]),0)
            CmdWin.insert(1.0, "\n[User] Username: " + user.name)

    
    userentry.delete(0, END)

def do_List():
    CmdWin.insert(1.0, "\nPress List")
    global CONNECTED_ROOM, sockfd

    # check if client has established TCP connection with room server
    if not CONNECTED_ROOM:

        # establish TCP connection
        success , res = tcp_connect(sys.argv[1],sys.argv[2])
        # check if connection is successful
        if not success:
            CmdWin.insert(1.0, "\n[Reject-List] " + res)
            return
        else:
            sockfd = res

        CONNECTED_ROOM = True
        CmdWin.insert(1.0, "\n[List] connected to server")
    
    # send 'L' request to room server
    request = "L::\r\n"
    status = send_request(sockfd, request)
    # check if socket.send is successful
    if not status:
        CmdWin.insert(1.0, "\n[Reject-List] " + res)
        return

    # receive response from room server
    rmsg = sockfd.recv(1000)
    rmsg = rmsg.decode("ascii") 
    # check if successfully receive response from room server
    if rmsg:
        # print("P: Received a list message")
        CmdWin.insert(1.0, "\n[List] " + rmsg)
    else:
        # print("E: Client connection is broken!!")
        CmdWin.insert(1.0, "\n[Reject-List] Client connection is broken")
        CONNECTED_ROOM = False
        # sys.exit(1)

    
def do_Join():
    global NAMED, JOINED, CONNECTED_ROOM, user, room, sockfd

    # check if user has registered username
    if not NAMED:
        CmdWin.insert(1.0, "\n[Reject-Join] You should register an username first")
        return
    # check if user input for chatroom name is empty
    if not userentry.get():
        CmdWin.insert(1.0, "\n[Reject-Join] You must provide the target chatroom name")
        return
    # check if user has joined a chatroom group before
    if JOINED:
        CmdWin.insert(1.0, "\n[Reject-Join] You cannnot join new chatroom group \
                  since you have already joined a  group:" + room.name)
        return


    # check if client has established TCP connection with room server
    if not CONNECTED_ROOM:   
        # establish TCP connection
        success , res = tcp_connect(sys.argv[1],sys.argv[2])
        # check if connection is successful
        if not success:
            CmdWin.insert(1.0, "\n[Reject-Join] " + res)
            return
        else:
            sockfd = res

        CONNECTED_ROOM = True
        CmdWin.insert(1.0, "\n[Join] connected to server")
    if not room:
        roomname = userentry.get()
        room = Room(userentry.get(), sys.argv[1], int(sys.argv[2]))
        room.sockfd = sockfd       
    # send 'J' request to room server
    status = j_req(user,room)
    # check if socket.send is successful
    if not status:
        CmdWin.insert(1.0, "\n[Reject-Join] " + res)
        return

    # receive response from room server
    status, rmsg = recv_message(room.sockfd, 1000)
    # check if successfully receive response from room server
    if not status:
        # print("E: Client connection is broken!!")
        CmdWin.insert(1.0, "\n[Reject-Join] Client connection is broken")
        CONNECTED_ROOM = False
        return
    if status and rmsg:
        if rmsg[0] == "F":
            CmdWin.insert(1.0, "\n[Reject-Join] " + rmsg)
            return
        # print("P: Received a join message")
        CmdWin.insert(1.0, "\n[Join] " + rmsg)
        JOINED = True

    choose_forward(rmsg)
    
    #start keepalive
    if room.keepalive_th:
        room.keepalive_th.close()
    keepalive = threading.Thread(name="keepalive_th", target=keepalive_th, args=('Join',))
    keepalive.start()
    room.keepalive_th = keepalive
    
    #start listening to request
    if not room.listen_th:
        listen = threading.Thread(name="listen_th", target=listen_th,args=())
        listen.start()
        room.listen_th = listen
    
    userentry.delete(0, END)


def do_Send():
    global CONNECTED_ROOM, JOINED, gLock, room, user
    if not userentry.get() or not CONNECTED_ROOM or not JOINED:
        return
    message = userentry.get()
    MsgWin.insert(1.0, "\n" + user.name + ":" + message)
#T:roomname:originHID:origin_username:msgID:msgLength:Message content::\r\n
    msg = "T:" + room.name +":"+ str(user.hashid)+":"+user.name +":"+ str(max(user.msgid) + 1) +":" \
    + str(len(message)) +":"+ str(message) + "::\r\n"
    #update user's message id 
    user.msgid.append(max(user.msgid) + 1)
    room.getPeer(user.hashid).msgid = user.msgid

    room.sendAll(msg)

    CmdWin.insert(1.0, "\nPress Send")
    userentry.delete(0, END)


def do_Quit():

    global gLock, room, quit_alert
    
    quit_alert = True
    if not room:
        sys.exit(0)
    # close all socket
    gLock.acquire()
    for peer in room.peers:
        if peer.sockfd:
            peer.sockfd.close()
    gLock.release()
    print("socket closed")
    # join listen_th
    if room.listen_th:
        room.listen_th.join()
    print("listening thread closed")
    # join peers_ths
    for t in room.peers_ths:
        t.join()
    print("peers_ths closed")
    # join keepalive
    if room.keepalive_th:
        room.keepalive_th.join()
    print("keepalive_th closed")

    CmdWin.insert(1.0, "\nPress Quit")
    sys.exit(0)

#
# Set up of Basic UI
#
win = Tk()
win.title("MyP2PChat")

#Top Frame for Message display
topframe = Frame(win, relief=RAISED, borderwidth=1)
topframe.pack(fill=BOTH, expand=True)
topscroll = Scrollbar(topframe)
MsgWin = Text(topframe, height='15', padx=5, pady=5, fg="red", exportselection=0, insertofftime=0)
MsgWin.pack(side=LEFT, fill=BOTH, expand=True)
topscroll.pack(side=RIGHT, fill=Y, expand=True)
MsgWin.config(yscrollcommand=topscroll.set)
topscroll.config(command=MsgWin.yview)

#Top Middle Frame for buttons
topmidframe = Frame(win, relief=RAISED, borderwidth=1)
topmidframe.pack(fill=X, expand=True)
Butt01 = Button(topmidframe, width='8', relief=RAISED, text="User", command=do_User)
Butt01.pack(side=LEFT, padx=8, pady=8);
Butt02 = Button(topmidframe, width='8', relief=RAISED, text="List", command=do_List)
Butt02.pack(side=LEFT, padx=8, pady=8);
Butt03 = Button(topmidframe, width='8', relief=RAISED, text="Join", command=do_Join)
Butt03.pack(side=LEFT, padx=8, pady=8);
Butt04 = Button(topmidframe, width='8', relief=RAISED, text="Send", command=do_Send)
Butt04.pack(side=LEFT, padx=8, pady=8);
Butt05 = Button(topmidframe, width='8', relief=RAISED, text="Quit", command=do_Quit)
Butt05.pack(side=LEFT, padx=8, pady=8);

#Lower Middle Frame for User input
lowmidframe = Frame(win, relief=RAISED, borderwidth=1)
lowmidframe.pack(fill=X, expand=True)
userentry = Entry(lowmidframe, fg="blue")
userentry.pack(fill=X, padx=4, pady=4, expand=True)

#Bottom Frame for displaying action info
bottframe = Frame(win, relief=RAISED, borderwidth=1)
bottframe.pack(fill=BOTH, expand=True)
bottscroll = Scrollbar(bottframe)
CmdWin = Text(bottframe, height='15', padx=5, pady=5, exportselection=0, insertofftime=0)
CmdWin.pack(side=LEFT, fill=BOTH, expand=True)
bottscroll.pack(side=RIGHT, fill=Y, expand=True)
CmdWin.config(yscrollcommand=bottscroll.set)
bottscroll.config(command=CmdWin.yview)

def main():
    if len(sys.argv) != 4:
        print("P2PChat.py <server address> <server port no.> <my port no.>")
        sys.exit(2)

    win.mainloop()

if __name__ == "__main__":
    main()

