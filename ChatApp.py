from socket import socket, AF_INET, SOCK_DGRAM
import argparse
import UDPClient, UDPServer

def is_valid_ipv4_address(address):
    if address.lower() == "localhost":
        return True

    # Split the string into four parts separated by dots
    parts = address.split('.')
    if len(parts) != 4:
        return False

    # Check that each part is an integer between 0 and 255
    for part in parts:
        try:
            num = int(part)
        except ValueError:
            return False
        if num < 0 or num > 255:
            return False

    return True


#will eventually have to start the app using ChatApp -c <name> 
if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='ChatApp')
    
    # Client Arguments
   
    parser.add_argument('-c', '--clientName', type=str, help='Name of the client')
    parser.add_argument('args', metavar='arg', type=str, nargs='*', help='Command line arguments')

    # Server Arguments
    parser.add_argument('-s', '--server', action='store_true', help='Run as a server')

    args = parser.parse_args()

    # Now you can access the values of the arguments as follows:

    # Check if the program is running as a server or client
    if args.server:
        # The program is running as a server
        if len(args.args) != 1:
            raise Exception("Input should be ChatApp.py -s <port>")

        serverPort = int(args.args[0])
        if serverPort < 1024 or serverPort > 65535:
            raise Exception("Should be a port between 1024 and 65535")

        UDPServer.serverMode(serverPort)
    else:
        # The program is running as a client 
        
        if len(args.args) != 3:
            raise Exception("Input should be ChatApp.py -c <name> <server-ip> <server-port> <client-port>")
        
        clientName = args.clientName
        clientIP = args.args[0]
        
        if not is_valid_ipv4_address(clientIP):
            raise Exception("Should be a valid IP address")

        serverPort = int(args.args[1])
        clientPort = int(args.args[2])

        if clientPort < 1024 or clientPort > 65535 or serverPort < 1024 or serverPort > 65535:
            raise Exception("Should be a port between 1024 and 65535")

        UDPClient.clientMode(clientName, clientIP, serverPort, clientPort)
        