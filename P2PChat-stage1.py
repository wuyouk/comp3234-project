#!/usr/bin/python3

# Student name and No.:	Wu You - 3035086120
# Student name and No.: Zhu Youwei - 3035087198
# Development platform: Mac
# Python version: Python 3.5.0
# Version: 1

# Command
# cd Desktop/S2Courses/COMP3234_Computer\ and\ Communication\ Networks/Project/comp3234-project/
# python3 P2PChat-stage1.py 147.8.94.112 32340 33333

from tkinter import *

import sys
import socket
import time

import threading

#
# Global variables
#
NAMED = False
JOINED = False
CONNECTED_ROOM = False
username = ""
sockfd = None
roomname = ""

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


#
# Functions to handle user input
#


# function to establish TCP connection, return a socket object sockfd
def connect():
	try:
		sockfd = socket.socket()
		sockfd.connect((sys.argv[1], int(sys.argv[2])))
	except socket.error as emsg:
		print("Socket connect error:", emsg)
		return False, emsg
		# sys.exit(1)
	return True, sockfd


# function to send TCP request, return a str
def send_request(sockfd, request):
	try:
		sockfd.send(request)
	except socket.error as emsg:
		print("E: Socket send error:", emsg)
		return "Socket send error: " + str(emsg)
		# sys.exit(1)
	return "OK"



# function to keepalive by sending join requests
def keepalive(action):
	global JOINED, CONNECTED_ROOM, username, roomname, sockfd
	while (True):
		while (JOINED and CONNECTED_ROOM):
			time.sleep(20)
			request = "J:" + str(roomname) + ":" + str(username) + ":"\
			       + str(sockfd.getsockname()[0]) + ":" + str(sockfd.getsockname()[1])\
			       + "::\r\n"
			res = send_request(sockfd, request.encode('ascii'))
			# check if socket.send is successful
			if res != "OK":
				CmdWin.insert(1.0, "\n[Reject-" + action + "] " + res)
				
			# receive response from room server
			rmsg = sockfd.recv(1000)
			rmsg = rmsg.decode("ascii")
			# check if successfully receive response from room server
			if rmsg:
				if rmsg[0] == "F":
					CmdWin.insert(1.0, "\n[Reject-" + action + "] " + rmsg)
					
				CmdWin.insert(1.0, "\n[" + action + "] " + rmsg)
				JOINED = True
			else:
				CmdWin.insert(1.0, "\n[Reject-" + action + "] Client connection is broken")
				CONNECTED_ROOM = False


def do_User():
	global JOINED, NAMED, username
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
			username = userentry.get()
			CmdWin.insert(1.0, "\n[User] Username: " + username)

	
	userentry.delete(0, END)

def do_List():
	CmdWin.insert(1.0, "\nPress List")
	global CONNECTED_ROOM, sockfd

	# check if client has established TCP connection with room server
	if not CONNECTED_ROOM:
		# establish TCP connection
		success , res = connect()
		# check if connection is successful
		if not success:
			CmdWin.insert(1.0, "\n[Reject-List] " + res)
			return
		else:
			sockfd = res

		print("P: Connection established. My socket address is", sockfd.getsockname())
		CONNECTED_ROOM = True
		CmdWin.insert(1.0, "\n[List] connected to server")
	
	# send 'L' request to room server
	request = "L::\r\n".encode('ascii')
	res = send_request(sockfd, request)
	# check if socket.send is successful
	if res != "OK":
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
	global NAMED, JOINED, CONNECTED_ROOM, username, roomname, sockfd

	# check if user has registered username
	if not NAMED:
		CmdWin.insert(1.0, "\n[Reject-Join] You should register an username first")
		return
	# check if user input for chatroom name is empty
	if not userentry.get():
		CmdWin.insert(1.0, "\n[Reject-Join] You must provide the target chatroom name")
		return

	roomname = userentry.get()

	# check if user	has joined a chatroom group before
	if JOINED:
		CmdWin.insert(1.0, "\n[Reject-Join] You cannnot join new chatroom group \
				  since you have already joined a chatroom group")
		return

	# check if client has established TCP connection with room server
	if not CONNECTED_ROOM:
		# establish TCP connection
		success , res = connect()
		# check if connection is successful
		if not success:
			CmdWin.insert(1.0, "\n[Reject-Join] " + res)
			return
		else:
			sockfd = res

		print("P: Connection established. My socket address is", sockfd.getsockname())
		CONNECTED_ROOM = True
		CmdWin.insert(1.0, "\n[Join] connected to server")
			
	# send 'J' request to room server
	request = "J:" + str(roomname) + ":" + str(username) + ":"\
			       + str(sockfd.getsockname()[0]) + ":" + str(sockfd.getsockname()[1])\
			       + "::\r\n"

	res = send_request(sockfd, request.encode('ascii'))
	# check if socket.send is successful
	if res != "OK":
		CmdWin.insert(1.0, "\n[Reject-Join] " + res)
		return

	# receive response from room server
	rmsg = sockfd.recv(1000)
	rmsg = rmsg.decode("ascii") 
	# check if successfully receive response from room server
	if rmsg:
		if rmsg[0] == "F":
			CmdWin.insert(1.0, "\n[Reject-Join] " + rmsg)
			return
		# print("P: Received a join message")
		CmdWin.insert(1.0, "\n[Join] " + rmsg)
		JOINED = True
	else:
		# print("E: Client connection is broken!!")
		CmdWin.insert(1.0, "\n[Reject-Join] Client connection is broken")
		CONNECTED_ROOM = False
		return

	thread_join = threading.Thread(name="thread_join", target=keepalive, args=('Join',))
	thread_join.start()

	userentry.delete(0, END)


def do_Send():
	CmdWin.insert(1.0, "\nPress Send")


def do_Quit():
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

