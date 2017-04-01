#!/usr/bin/python3

# Student name and No.:	Wu You - 3035086120
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
room = None	# class Room
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
	except socket.error as err:
		print("Receive Error:", err)

	if rmsg:
		return True, rmsg # 
	else:
		return False, "" # broken connection return false 

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

    def getHashId(self):
        str = str(self.name) + str(self.ip) + str(self.port)
        return sdbm_hash(str)

    def getHashId(self, user):
        str = str(user.name) + str(user.ip) + str(user.port)
        return sdbm_hash(str)

    def disconnect(self):
    	self.isconnected = False
    	self.isforward = False
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
		self.listen_th = None # listening to income request
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
		for peer in peers:
			if peer.hashid == cur_id:
				return True
		return False

	def getPeer(self, user):
		for peer in peers:
			if peer.hashid == user.hashid:
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
			if peer.connected:
				status = send_request(peer.sockfd,message)
				if not status:
					peer.disconnect()

#
# Helper Functions 
#

# JOIN related
# function to send join request: J:roomname:username:userIP:userPort::\r\n
def j_req(user,room):
	request = "J:" + str(room.name) + ":" + str(user.name) + ":"\
			       + str(user.ip) + ":" + str(user.port)\
			       + "::\r\n"
	status = send_request(room.sockfd, request)
	return status

# function to get peers from join request response:
# example: J:tom:ip:port return room contains tom's information
def j_res_parse(rmsg):
	msg = rmsg.split(":")
	peer_list = []
	i = 2 # M:MSID:userA user information start at index 2
	while (i < len(msg)):
	    try:
	        cur = Peer(msg[i], msg[i + 1], int(msg[i + 2]),0)
	    except ValueError:
	        print ('Can not parse rmsg in choose_forward')
	    peer_list.append(cur)
	    i = i + 3
	return Room(peers = peer_list)

# Peer to Peer related
# send peer connection request
def p_req(sender, target, room):
	msg = "P:" + room.name + ":" + sender.name + ":" + sender.ip + ":" + \
	str(sender.port) + ":" + max(sender.msgid) + "::\r\n"
	status = send_request(target.sockfd, msg)
	if status:
		s2, rmsg = recv_message(passive.sockfd, 1000)
		return s2
	return False

# send peer connection response
def p_res(sender, target, room):
	msg = "S:" + max(sender.msgid) + "::\r\n"
	status = send_request(target.sockfd, msg)
	return status
# function to get peer from p request message:
def p_req_parse(rmsg,room):
	msg = rmsg.split(":")
	# check header and room information
	if msg[0] != "P" or msg[1] != room.name
		return False, None
	# extract peer
	try:
	    cur = Peer(msg[2], msg[3], int(msg[4]),int(msg[5]))
	except ValueError:
	    print ('Can not parse rmsg in choose_forward')
	if room.peers.hasPeer(cur):
		peer = room.getPeer(cur)
		peer.msgid = []
		peer.msgid.append(int(msg[5]))
		return True, peer
	else:
		return False, None

# Text message:
#send a message
#T:roomname:originHID:origin_username:msgID:msgLength:Message content::\r\n
def send_t(user, target, room, message):
	msg = "T:" + room.name + ":" + str(user.hashid) + ":" + user.name + \
	":" + max(user.msgid) + ":" + len(message) + ":" + message + "::\r\n"
	status = send_request(target.sockfd, msg)
	return status

def parse_t(room, rmsg):
	msg = rmsg.split(":")
	hashid = int(msg[2])
	msgid = int(msg[4])
	if room.hasPeer(hashid):
		if msgid not in room.getPeer(hashid).msgid
			return True, msg[3], msg[6]
	return False, None, None

# check if the forward message is from a peer in the chat room
def forward_valid(room, message):
	msg = message.split(":")
	hashid = int(msg[2])
	roomname = msg[1]
	return roomname == room.name and room.hasPeer(hashid)

# function to set up forward link
def choose_forward(rmsg):
	global room, user

	cur_room = j_res_parse(rmsg)
	room.updatePeer(cur_room)
    #2.sort the membership by increasing order
    sorted(room.peers, key = lambda, peer: peer.hashid)

    #3.use H's hash id to find its index X in list
    myhashid = user.hashid
    start = 0
    for peer in room.peers:
    	curhid = peer.hashid
    	if curhid <= myhashid:
    		start++
    #4.
    my_index = start - 1
    established = False
    while (start != my_index):
    	if (start == len(room.peers)) start = 0
    	peer = room.peers[start]
    	if peer.isconnected:
    		start = (start + 1) % len(room.peers)
    	else 
    		# try to build forward link with this peer
    		success , sockfd = tcp_connect(peer.ip,peer.port)
    		if success:
    			peer.sockfd = sockfd
    			status = p_req(user, peer, room)
    			if status:
    				peer.forwardconnect()
    				established = True
    				break
    		else:
    			start = (start + 1) % len(room.peers)
    return established

# listening thread
def listen_th():
	global user, room
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
	while True:
		try:
			newfd, caddr = sockfd.accept()
		except socket.timeout:
			continue
		# peer to peer handshake
		should_add = False
		#parse received message of peer information
		status, rmsg = recv_message(newfd, 1000)
		if status and not rmsg:
			continue # timeout occurs
		if status and rmsg:
			#check if peer in the room
			in_room, peer = p_req_parse(rmsg)
			if in_room:
				#if peer in the room
				should_add = True
			else:
				#if peer is unknown, send join request to update room
				status = j_req(room, user)
				status, rmsg2 = recv_message(room.sockfd,1000)
				if status:
					cur_room = j_res_parse(rmsg2)
					room.updatePeer(cur_room)
					#check if peer in the room again
					in_room, peer = p_req_parse(rmsg)
					if in_room:

						should_add = True
		else:
			newfd.close()
			continue
		# if peer is unknown continue
		if not should_add:
			newfd.close()
			continue
		# otherwise send the hand shake message to this peer and add to queue
		peer.sockfd = newfd
		peer.backwardconnect()
		msg = "S:" + str(max(user.msgid)) + "::\r\n"
		send_request(newfd, msg)

		peer_th = threading.Thread(target=peer_th, args=(peer,))
		peer_th.start()
		# add this new thread to cthread list
		room.peer_ths.append(thd)
	return

# thread to handle peer information
def peer_th(current):
	
	global gLock, room

	sockfd.settimeout(1.0)

	while (True):
		# wait for any message to arrive
		status, rmsg = recv_message(current.sockfd,1024)
		if status and not rmsg:
			continue # timeout occurs
		if status and rmsg:
			valid, name, body = parse_t(room, rmsg)
			if not valid:
				continue
			msg = name + ":" + body
			CmdWin.insert(1.0,"\n" + msg)
			gLock.acquire()
			for peer in room.peers:
				if peer.isconnected:
					success = send_request(current.sockfd,rmsg)
					if not success:
						peer.disconnect()
			gLock.release()
		# else a broken connection is detected, do the following
		# use mutex lock gLock to protect the access of WList
		else:
			gLock.acquire()
			current.disconnect()
			gLock.release()
			break
	return

# thread to keepalive by sending join requests
def keepalive_th(action):
	global JOINED, CONNECTED_ROOM, user, room
	while (True):
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
			CmdWin.insert(1.0, "\n[Reject-" + action + "] Client connection is broken")
			CONNECTED_ROOM = False





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
	global CONNECTED_ROOM, room

	# check if client has established TCP connection with room server
	if not CONNECTED_ROOM:
		# establish TCP connection
		success , res = tcp_connect(sys.argv[1],sys.argv[2])
		# check if connection is successful
		if not success:
			CmdWin.insert(1.0, "\n[Reject-List] " + res)
			return
		else:
			room.sockfd = res

		CONNECTED_ROOM = True
		CmdWin.insert(1.0, "\n[List] connected to server")
	
	# send 'L' request to room server
	request = "L::\r\n".encode('ascii')
	status = send_request(room.sockfd, request)
	# check if socket.send is successful
	if not status:
		CmdWin.insert(1.0, "\n[Reject-List] " + res)
		return

	# receive response from room server
	rmsg = room.sockfd.recv(1000)
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
	global NAMED, JOINED, CONNECTED_ROOM, user, room

	# check if user has registered username
	if not NAMED:
		CmdWin.insert(1.0, "\n[Reject-Join] You should register an username first")
		return
	# check if user input for chatroom name is empty
	if not userentry.get():
		CmdWin.insert(1.0, "\n[Reject-Join] You must provide the target chatroom name")
		return

	roomname = userentry.get()
	room = Room(userentry.get(), sys.argv[1], int(sys.argv[2]))

	# check if user	has joined a chatroom group before
	if JOINED:
		CmdWin.insert(1.0, "\n[Reject-Join] You cannnot join new chatroom group \
				  since you have already joined a chatroom group")
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
			room.sockfd = res

		CONNECTED_ROOM = True
		CmdWin.insert(1.0, "\n[Join] connected to server")
			
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
	keepalive_th = threading.Thread(name="keepalive_th", target=keepalive_th, args=('Join',))
	keepalive_th.start()
	room.keepalive_th = keepalive_th
	#start listening to request
	listen_th = threading.Thread(name="listen_th", target=listen_th,args=(user.sockfd,))
	listen_th.start()
	room.listen_th = listen_th
	userentry.delete(0, END)


def do_Send():
	global CONNECTED_ROOM, JOINED gLock, room, user
	if not userentry.get() or not CONNECTED_ROOM or not JOINED:
		return
	message = userentry.get()

	msg = "T:" + room.name +":"+ user.name +":"+ str(max(user.msgid)) +":"+ \
	+ str(len(message)) +":"+ message + "::\r\n"
	#update user's message id 
	user.msgid.append(max(user.msgid) + 1)
	room.sendAll(msg)
	userentry.delete(0, END)


def do_Quit():

	global gLock, room
	# close all socket
	gLock.acquire()
	for peer in room.peers:
		if peers.sockfd:
			peers.sockfd.close()
	# join all threads to terminate before termination of main thread
	for t in room.peers_ths:
		t.join()
	room.keepalive_th.join()
	room.listen_th.join()
	gLock.release()

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

# keepalive('Join')

def main():
	if len(sys.argv) != 4:
		print("P2PChat.py <server address> <server port no.> <my port no.>")
		sys.exit(2)

	win.mainloop()

if __name__ == "__main__":
	main()

