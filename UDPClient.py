from socket import socket, AF_INET, SOCK_DGRAM
import ChatApp
import threading
import time
from multiprocessing import Value

clientName_table = set() #local table for clients
client_table = {}

usersPrivateMessaged = {} #for private messaging between clients
buffered_private_messages = {}
serverResponding = Value('b', False)

userGroup = ""

def updateTable(clientName, clientIP, clientPort, clientStatus):
    clientName_table.add(clientName)
    client_table[clientName] = (clientName, clientIP, clientPort, clientStatus)

#this is where messages are received and responses to those mesages are sent out
def clientListen(clientName, serverIP, clientPort, serverPort): #pass in the sender socket here
    print(">>> [Welcome, You are registered.]")
    global clientSocket
    global userGroup
    global buffered_private_messages

    clientSocket = socket(AF_INET, SOCK_DGRAM)
    clientSocket.connect((serverIP, serverPort))

    listen_socket = socket(AF_INET, SOCK_DGRAM)
    listen_socket.bind(('', clientPort))
    newEntry = True

    while True:
        
        if newEntry: #request the rest of the table
            msg = "REQUEST_TABLE\n" + str(clientPort) + "\n" + serverIP
            clientSocket.sendto(msg.encode(), (serverIP, serverPort))
            newEntry = False

        sender_message, sender_address = listen_socket.recvfrom(4096)
        sender_message = sender_message.decode()
      
        lines = sender_message.splitlines()

        if userGroup != "": #means that the user belongs to a group
            if lines[0] == "close":
                listen_socket.close()
                return
            elif lines[0] == "leave_group":
                serverResponding.value = True
                print(">>> [Leave group chat <" + userGroup + ">]")
                userGroup = ""

                for client in buffered_private_messages.keys():
                    list_of_messages = buffered_private_messages[client]
                    for message in list_of_messages:
                        print("$ >>> " + client + ": " + message)

                buffered_private_messages = {} #empty out the dictionary
            elif lines[0] == "list_members":
                serverResponding.value = True
                print(">>> (<"+userGroup+">) [Members in the group <"+userGroup+">:]")

                for i in range(1, len(lines)):
                    print("$ >>> (<" +userGroup+">) <"+ lines[i]+">")
            elif lines[0] == "group_message_sent":
                serverResponding.value = True
                print(">>> (" + userGroup + ") [Message received by Server.]")
            elif lines[0] == "group_message":
                senderName = lines[1]
                msg = lines[2]
                ack = "received_group_message"
                clientSocket.sendto(ack.encode(), (serverIP, serverPort))
                print(">>> Group_Message <("+senderName+")>: <"+msg+">.")          
            elif lines[0] == "UPDATEDTABLE": #update the local table (handles reg/dereg)
                for i in range(1, len(lines), 4):
                    newClientName = lines[i]
                    newClientIP = lines[i+1]
                    newClientPort = lines[i+2]
                    newClientStatus = lines[i+3]
                    updateTable(newClientName, newClientIP, newClientPort, newClientStatus)
                print("[Client table updated.]")
            elif lines[0] == "send": #ACK Response created by private message client recipient
                senderName = lines[3]
                msg = lines[2]
                client_port = int(lines[1])
                client_ip = client_table[clientName][1]
                if senderName not in buffered_private_messages.keys():
                    buffered_private_messages[senderName] = [msg]
                else:
                    buffered_private_messages[senderName].append(msg)
                msg="PRIVATE_MESSAGE\n" + "ACK\n" + str(clientName) + "\n"
                clientSocket.sendto(msg.encode(), (client_ip, client_port))
        else: #the user does not belong to a group
            
            if lines[0] == "close":
                listen_socket.close()
                break
            elif lines[0] == "joined_group":
                userGroup = lines[1]
                msg = lines[2]
                print(msg)
                serverResponding.value = True
            elif lines[0] == "groupDNE": #the user tries to join a group, but it DNE
                msg = lines[1]
                print(msg)
                serverResponding.value = True
            elif lines[0] == "list_groups":
                print(">>> [Available group chats:]")
            
                for i in range(1, len(lines)):
                    print("$ >>> " + lines[i])
                serverResponding.value = True

            elif lines[0] == "group_created" or lines[0] == "group_exists":
                msg = lines[1]
                print(msg)
                serverResponding.value = True
            elif lines[0] == "UPDATEDTABLE": #update the local table (handles reg/dereg)
                for i in range(1, len(lines), 4):
                    newClientName = lines[i]
                    newClientIP = lines[i+1]
                    newClientPort = lines[i+2]
                    newClientStatus = lines[i+3]
                    updateTable(newClientName, newClientIP, newClientPort, newClientStatus)
                print("[Client table updated.]")
            elif lines[0] == "send": #ACK Response created by private message client recipient
                senderName = lines[3]
                client_ip = client_table[clientName][1]
                msg = lines[2] 
                client_port = int(lines[1])
                output = ">>> <" + senderName + ">: <" + msg + ">"
                print(output)
                msg="PRIVATE_MESSAGE\n" + "ACK\n" + str(clientName) + "\n"            
                clientSocket.sendto(msg.encode(), (client_ip, client_port)) 
            elif lines[0] == "PRIVATE_MESSAGE": #ACK Response created by private message client sender
                ack = lines[1]
                destination = lines[2]
                usersPrivateMessaged[destination] = True
                print("Message received by", destination)
            elif lines[0] == "ack" or lines[0] == "dereg": #General ACK Response
                serverResponding.value = True
                if lines[0] == "ack":
                    msg = lines[2]
                    print("Received message: ", msg, " from the sender.")
            elif lines[0] == "invalid_reg":
                print("Cannot register user with a name that is already within the system.")


def clientMode(clientName, IP, serverPort, clientPort):
    
    #socket
    global userGroup
    global clientSocket
    clientSocket = socket(AF_INET, SOCK_DGRAM)
    #send first message - may already be registered, or not.
    first_message = "registration\n" + str(clientPort)  + "\n" + IP + "\n" + clientName
    clientSocket.sendto(first_message.encode(), (IP, serverPort))


#multi-threading
    listen = threading.Thread(target=clientListen, args=(clientName, IP, clientPort, serverPort))
    listen.start()

    while True:
        if userGroup == "":
            print(">>> ", end="")
        else:
            print(">>> ("+userGroup+") ", end="")
        
        temp = input()

        if temp == "ctrl + c":
            print("Exiting.")
            msg = "close\n"
            clientSocket.sendto(msg.encode(), (IP, clientPort))
            clientSocket.close()
            listen.join()
            return

        input_list = temp.split()

        try:
            header = input_list[0]
        except:
            print("\n>>>Invalid input")
            continue

        if userGroup != "":
           
            if header == "leave_group":
                to_send = "leave_group\n" + userGroup + "\n" + str(clientPort) + "\n" + clientName
                serverResponding.value = False

                for i in range(5):
                    clientSocket.sendto(to_send.encode(), (IP, serverPort))
                    time.sleep(0.5)

                    if serverResponding.value == True:
                        break

                if serverResponding.value == False:
                    print(">>> ("+userGroup+") [Server not responding.]")
                    print(">>> ("+userGroup+") [Exiting]")
                    msg = "close\n"
                    clientSocket.sendto(msg.encode(), (IP, clientPort))
                    clientSocket.close()
                    listen.join()
                    return
            elif header == "list_members":
                to_send = "list_members\n" + userGroup + "\n" + str(clientPort) + "\n" + clientName

                serverResponding.value = False

                for i in range(5):
                    clientSocket.sendto(to_send.encode(), (IP, serverPort))
                    time.sleep(0.5)

                    if serverResponding.value == True:
                        break

                if serverResponding.value == False:
                    print(">>> ("+userGroup+") [Server not responding.]")
                    print(">>> ("+userGroup+") [Exiting]")
                    msg = "close\n"
                    clientSocket.sendto(msg.encode(), (IP, clientPort)) 
                    clientSocket.close()
                    listen.join()
                    return
            elif header == "send_group":
                
                if len(input_list) == 1:
                    print("Please add a message to the send_group command")
                    continue

                message = ""
                for i in range(1, len(input_list)):
                    if i != len(input_list) - 1:
                        message+=input_list[i] + " " 
                    else:
                        message+=input_list[i]

                to_send = "send_group\n" + userGroup + "\n" + message + "\n" + str(clientPort) + "\n" + clientName

                serverResponding.value = False
                for i in range(5):
                    clientSocket.sendto(to_send.encode(), (IP, serverPort))
                    time.sleep(0.5)

                    if serverResponding.value == True:
                        break

                if serverResponding.value == False:
                    print(">>> ("+userGroup+") [Server not responding.]")
                    print(">>> ("+userGroup+") [Exiting]")
                    msg = "close\n"
                    clientSocket.sendto(msg.encode(), (IP, clientPort)) 
                    clientSocket.close()
                    listen.join()
                    return

            elif header == "dereg":
               
                if len(input_list) == 1:
                    print("Please add a client name to the dereg command")
                    continue
                
                destination = input_list[1]

                if destination != clientName:
                    print(">>> [Invalid command]")
                    continue

                destination_info = client_table[destination]
                #destination_info = (clientName, clientIP, clientPort, clientStatus)
                destinationIP = destination_info[1]
                destinationPort = int(destination_info[2])
                recipient_address = (destinationIP, destinationPort)

                to_send = "dereg_group\n" + userGroup + "\n" + str(clientPort) + "\n" + clientName

                serverResponding.value = False

                for i in range(5):
                    clientSocket.sendto(to_send.encode(), (IP, serverPort))
                    time.sleep(0.5)
        
                    if serverResponding.value == True:
                        print(">>> [You are Offline. Bye.]")
                        break

                if serverResponding.value == False:
                    print(">>> [Server not responding]")
                    print(">>> [Exiting]")

                msg = "close\n"
                clientSocket.sendto(msg.encode(), (IP, clientPort)) 
                clientSocket.close()
                listen.join()
                return

            else:
                print(">>> ("+userGroup+"> [Invalid command]")
        else:
            if header == "join_group":
                
                if len(input_list) == 1:
                    print("Please add a group name to the join_group command")
                    continue

                groupName = ""
                for i in range(1, len(input_list)):
                    if i != len(input_list) - 1:
                        groupName = groupName + input_list[i] + " "
                    else:
                        groupName+=input_list[i]
            
                to_send = "join_group\n" + groupName + "\n" + str(clientPort) + "\n" + clientName
                serverResponding.value = False

                for i in range(5):
                    clientSocket.sendto(to_send.encode(), (IP, serverPort))
                    time.sleep(0.5)

                    if serverResponding.value == True:
                        break
            
                if serverResponding.value == False:
                    print(">>> [Server not responding]")
                    print(">>> [Exiting]")
                    msg = "close\n"
                    clientSocket.sendto(msg.encode(), (IP, clientPort)) 
                    clientSocket.close()
                    listen.join()
                    return
            elif header == "list_groups":
                to_send = "list_groups\n" + str(clientPort) + "\n" + clientName
                serverResponding.value = False

                for i in range(5):
                    clientSocket.sendto(to_send.encode(), (IP, serverPort))
                    time.sleep(0.5)

                    if serverResponding.value == True:
                        break

                if serverResponding.value == False:
                    print(">>> [Server not responding]")
                    print(">>> [Exiting]")
                    msg = "close\n"
                    clientSocket.sendto(msg.encode(), (IP, clientPort)) 
                    clientSocket.close()
                    listen.join()
                    return
            elif header == "create_group":
                
                if len(input_list) == 1:
                    print("Please add a group name to the create_group command")
                    continue

                groupName = ""
                for i in range(1, len(input_list)):
                    if i != len(input_list) - 1:
                        groupName = groupName + input_list[i] + " "
                    else:
                        groupName+=input_list[i]

                to_send = "create_group\n" + groupName + "\n" + str(clientPort) + "\n" + clientName
                serverResponding.value = False

                for i in range(5):
                    clientSocket.sendto(to_send.encode(), (IP, serverPort))
                    time.sleep(0.5)

                    if serverResponding.value == True:
                        break

                if serverResponding.value == False:
                    print(">>> [Server not responding]")
                    print(">>> [Exiting]")
                    msg = "close\n"
                    clientSocket.sendto(msg.encode(), (IP, clientPort)) 
                    clientSocket.close()
                    listen.join()
                    return
            elif header == "dereg":
               
                if len(input_list) == 1:
                    print("Please add a client name to the dereg command")
                    continue
                
                destination = input_list[1]

                if destination != clientName:
                    print(">>> [Invalid command]")
                    continue

                destination_info = client_table[destination]
                #destination_info = (clientName, clientIP, clientPort, clientStatus)
                destinationIP = destination_info[1]
                destinationPort = int(destination_info[2])
                recipient_address = (destinationIP, destinationPort)

                to_send = "dereg\n" + str(clientPort) + "\n" + clientName
                serverResponding.value = False

                for i in range(5):
                    clientSocket.sendto(to_send.encode(), (IP, serverPort))
                    time.sleep(0.5)
        
                    if serverResponding.value == True:
                        print(">>> [You are Offline. Bye.]")
                        break

                if serverResponding.value == False:
                    print(">>> [Server not responding]")
                    print(">>> [Exiting]")

                msg = "close\n"
                clientSocket.sendto(msg.encode(), (IP, clientPort)) 
                clientSocket.close()
                listen.join()
                return

            elif header == "send":

                if len(input_list) < 3:
                    print("Please attach a message/client name to the send command")
                    continue

                destination = input_list[1]
            
                if destination not in clientName_table:
                    print("Messaege recipient not in client table.")
                else: 
                    destination_info = client_table[destination]
                    #destination_info = (clientName, clientIP, clientPort, clientStatus)
                    destinationIP = destination_info[1]
                    destinationPort = int(destination_info[2])
                    destinationStatus = destination_info[3]
                    
                    if destinationStatus == "No":
                        print("Client " + destination + " previously went offline")
                        continue

                    recipient_address = (destinationIP, destinationPort)
           
                    message = ""
                    for i in range(2, len(input_list)):
                        if i != len(input_list) - 1:
                            message = message + input_list[i] + " " 
                        else:
                            message+=input_list[i]

                    to_send =  "send\n" + str(clientPort) + "\n" + message + "\n" + clientName
                
                    usersPrivateMessaged[destination] = False
                    clientSocket.sendto(to_send.encode(), recipient_address)
                    time.sleep(0.5)        
   
                    if usersPrivateMessaged[destination] == False:

                        #private message global dictionary - group chat
                        #key:receiver port, value: false
                        #sleep 500ms.
                        #check whether the value in the key in the target is true.
                        #if true, it was ACKed
                        #ow, it wasn't received.
    
                        print("No ACK received from " + destination + ". Message not delivered")

                        offline_message = "BADACK\n" + str(destinationPort) + "\n" + destination

                        clientSocket.sendto(offline_message.encode(), (IP, serverPort))
                        del client_table[destination]
                        clientName_table.remove(destination)

                    usersPrivateMessaged[destination] = False
            else:
                print(">>> [Invalid command]")