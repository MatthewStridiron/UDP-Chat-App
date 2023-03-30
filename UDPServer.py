from socket import socket, AF_INET, SOCK_DGRAM
from multiprocessing import Value
import ChatApp
import threading
import time

clientName_table = set() #local table for clients
client_table = {}

group_chats = {}
flag = False

#General acknowledgement from the server
def generalACKResponse(server_socket, client_addr, client_port):
    ack = "ack\nMessage:\n'This is an ack from the server.'"
    server_socket.sendto(ack.encode(), (client_addr, client_port))

def serverResponse(msg, server_socket, client_addr, client_port):
    server_socket.sendto(msg.encode(), (client_addr, client_port))

'''
table functions
'''

#client_table[clientName] = (clientName, clientIP, client_port, "Yes")
def updateTable(serverSocket):
    updatedTable = "UPDATEDTABLE\n"
    for v in client_table.values():
        updatedTable+=(v[0] + "\n" + v[1] + "\n" + str(v[2]) + "\n" + v[3] + "\n")
    
    for v in client_table.values():
        if v[3] == "Yes":
            sendTable(updatedTable, serverSocket, v[1],int(v[2]))

#client_table[clientName] = (clientName, clientIP, client_port, "Yes")
def sendTable(entry, server_socket, client_addr, client_port):
    print("Server is sending an update table request to clientIP ", client_addr)
    server_socket.sendto(entry.encode(), (client_addr, client_port))


def ack_handle(serverSocket, clientIP, lines):
    global flag

    # get the header. the rest of the message depends on what the header is.
    header = lines[0]
    
    if header == "leave_group":
        groupName = lines[1]
        client_port = int(lines[2])
        clientName = lines[3]

        tuple_to_remove = ()
        for tup in group_chats[groupName]:
            if tup[0] == clientName:
                tuple_to_remove = tup
                break
        group_chats[groupName].remove(tuple_to_remove)

        print(">>> [Client <" + clientName + "> left group <" + groupName + ">]")
        msg = "leave_group\n"
        serverResponse(msg, serverSocket, clientIP, client_port)
    
    if header == "dereg_group":

        '''
        I think removing the client form the group is appropriate just to avoid waiting on acks for a client that is not active. However we don't specifically define the expected behavior so you can make design choices here.
        '''

        # remove it from the groupchat
        groupName = lines[1]
        client_port = int(lines[2])
        clientName = lines[3]

        tuple_to_remove = ()
        for tup in group_chats[groupName]:
            if tup[0] == clientName:
                tuple_to_remove = tup
                break
        group_chats[groupName].remove(tuple_to_remove)

        print(">>> [Client <" + clientName + "> left group <" + groupName + ">]")
        msg = "leave_group\n"
        serverResponse(msg, serverSocket, clientIP, client_port)

        # now update the clienttable since this user has been deregistered
        # del client_table[clientName]
        client_table[clientName] = (clientName, clientIP, client_port, "No")
        updateTable(serverSocket)
    
    if header == "list_members":
        groupName = lines[1]
        client_port = int(lines[2])
        clientName = lines[3]

        print(">>> [Client " + clientName + " requested listing members of group <"+groupName+">:]")
        msg = ""
        members = []
        for tuples in group_chats[groupName]:
            members.append(tuples[0])

        for i in range(0, len(members)):
            if i != len(members) - 1:
                msg = msg + "$ >>> " + members[i] + "\n"
            else:
                msg = msg + "$ >>> " + members[i]

        print(msg)

        msg = ""
        for i in range(0, len(members)):
            if i != len(members) - 1:
                msg = msg + members[i] + "\n"
            else:
                msg = msg + members[i]
        msg = "list_members\n" + msg
        serverResponse(msg, serverSocket, clientIP, client_port)
    
    if header == "received_group_message":
        flag = True
    
    if header == "send_group":

        groupName = lines[1]
        msg = lines[2]
        client_port = int(lines[3])
        clientName = lines[4]

        # group_chats[groupName] = (clientName, clientIP, client_port)
        print(">>> [Client " + clientName + " sent group message: <" + msg + ">]")

        ack = "group_message_sent\n"
        serverResponse(ack, serverSocket, clientIP, client_port)

        tuples_to_remove = []

        for tup in group_chats[groupName]:
            destinationName = tup[0]
            destinationIP = tup[1]
            destinationPort = tup[2]
            flag = False
            # client_table[clientName] = (clientName, client_ip, client_port, "Yes")
            if destinationName != clientName and client_table[destinationName][3] == "Yes": #if state explained: server is expecting an ack from all active clients
             #       print("within if statement")
                ack = "group_message\n" + clientName + "\n" +  msg

                # server_send = threading.Thread(target=serverResponse, args=(ack, serverSocket, destinationIP, destinationPort))
                # server_send.start()

                serverResponse(ack, serverSocket, destinationIP, destinationPort)
                time.sleep(0.1)
               
                if flag == False:
                    print(">>> [Client " + destinationName + " not responsive, removed from group " + groupName + "]")
                    tuples_to_remove.append(tup)
                    print("I should not be running this code.")
            
        #time.sleep(0.5)
        for t in tuples_to_remove:
            # print("I should not be runnin this code either!")
            destName = t[0]
            c_ip = t[1]
            c_port = int(t[2])
            group_chats[groupName].remove(t)

            print(">>> [Client <" + destName + "> left group <" + groupName + ">]")
            msg = "leave_group\n"
            serverResponse(msg, serverSocket, c_ip, c_port)

    if header == "join_group":
        groupName = lines[1]
        client_port = int(lines[2])
        clientName = lines[3]
        clientIP = client_table[clientName][1]

        msg = ""
        if groupName not in group_chats:
            msg += "groupDNE\n>>> [Group " + groupName + " does not exist]"
            print(">>> [Client " + clientName + " joining group " + groupName + " failed, group does not exist]")
        else:
            group_chats[groupName].add((clientName, clientIP, client_port))
            print(">>> [Client " + clientName + " joined group " + groupName + "]")
            msg += "joined_group\n" + groupName + "\n>>> [Entered group " + groupName + " successfully]"
            serverResponse(msg, serverSocket, clientIP, client_port)

    if header == "list_groups":

        # WHAT IF THERE ARE NO GROUPS
        client_port = int(lines[1])
        clientName = lines[2]

        print(">>> [Client " + clientName + " requested listing groups, current groups:]")
        msg = ""
        groups_list = list(group_chats.keys())

        for i in range(0, len(groups_list)):
            if i != len(groups_list) - 1:
                msg = msg + "$ >>> " + groups_list[i] + "\n"
            else:
                msg = msg + "$ >>> " + groups_list[i]

        print(msg)

        msg = ""
        for i in range(0, len(groups_list)):
            if i != len(groups_list) - 1:
                msg = msg + groups_list[i] + "\n"
            else:
                msg = msg + groups_list[i]
        msg = "list_groups\n" + msg
        serverResponse(msg, serverSocket, clientIP, client_port)

    if header == "create_group":
        groupName = lines[1]
        client_port = int(lines[2])
        clientName = lines[3]
        clientIP = client_table[clientName][1]

        msg = ""
        if groupName not in group_chats:
            group_chats[groupName] = set()
            print(">>> [Client " + clientName + " created group " + groupName + " successfully]")
            msg += "group_created\n>>> [Group " + groupName + " created by Server.]"
        else:
            print(">>> [Client " + clientName + " creating group " + groupName + " failed, group already exists]")
            msg += "group_exists\n>>> [Group " + groupName + " already exists.]"
        serverResponse(msg, serverSocket, clientIP, client_port)

    if header == "REQUEST_TABLE":
        updateTable(serverSocket)

    if header == "dereg" or header == "BADACK":
        clientName = lines[2]
        clientIP = client_table[clientName][1]
        client_port = int(client_table[clientName][2])

        # client_table[clientName] = (clientName, client_ip, client_port, "Yes")
        # del client_table[clientName]
        client_table[clientName] = (clientName, clientIP, client_port, "No")
        updateTable(serverSocket)
        if header == "dereg":
            msg = "dereg\n"
            serverResponse(msg, serverSocket, clientIP, client_port)
        else:
            generalACKResponse(serverSocket, clientIP, client_port)

    if header == "registration":
        client_port = int(lines[1])
        client_ip = lines[2]
        clientName = lines[3]

        # if clientName not in clientName_table:
        clientName_table.add(clientName)
        client_table[clientName] = (clientName, client_ip, client_port, "Yes")
        # can't I just call updateTable here and get rid of the UPDATE_TABLE SIGNAL?
        server_send = threading.Thread(target=generalACKResponse, args=(serverSocket, client_ip, client_port))
        server_send.start()

    print(client_table)

#will eventually have to start server process using ChatApp -s <port>
def serverMode(serverPort):
    
    #socket
    serverSocket = socket(AF_INET, SOCK_DGRAM)
    #bind
    serverSocket.bind(('', serverPort))
    print("Server is online")

    while True:
        #recv
        message, clientAddress = serverSocket.recvfrom(4096)
        #clientAddress = (clientIP, clientPort)

        clientIP = clientAddress[0]
        message = message.decode()
        lines = message.splitlines()

        t = threading.Thread(target=ack_handle, args=(serverSocket, clientIP, lines))
        t.start()