#!/usr/bin/python
import sys
import time
import socket
import select
import base64

# Socket options
delay = 0.0001
buffer_size = 4096

class Authenticate:
    """
    Authentication implementation that checks the Proxy-Authorization header for basic authentication.
    """

    def __init__(self, username, password):
        self.authenticated = False
        self.username = username
        self.password = password

    def authenticate(self, clientsock, clientaddr):
        """
        Authenticate the client using the Proxy-Authorization header.
        """
        auth_header = self.get_proxy_authorization_header(clientsock)
        if auth_header:
            uname, upass = self.decode_credentials(auth_header)
            if self.verify_user_account(uname, upass, clientaddr[0]):
                self.authenticated = True
                print("Client", clientaddr, "authenticated")
        return self.authenticated

    def get_proxy_authorization_header(self, client):
        """
        Extract the Proxy-Authorization header from the client request.
        """
        try:
            request = client.recv(4096)
            headers = request.split(b'\r\n')
            for header in headers:
                if header.lower().startswith(b'proxy-authorization: basic '):
                    return header.split(b' ')[-1].strip()
        except Exception as e:
            print(f"Error extracting authorization header: {e}")
        return None

    def decode_credentials(self, auth_header):
        """
        Decode the Base64 encoded username and password.
        """
        try:
            decoded_bytes = base64.b64decode(auth_header)
            decoded_str = decoded_bytes.decode('utf-8')
            uname, upass = decoded_str.split(':', 1)
            return uname, upass
        except Exception as e:
            print(f"Error decoding credentials: {e}")
            return None, None

    def verify_user_account(self, uname, upass, clientIp):
        """
        Verify the username and password against your authentication source.
        """
        # Example verification: hardcoded username and password
        # You should replace this with your actual verification logic
        return uname == self.username and upass == self.password

class Forward:

    def __init__(self):
        self.forward = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self, host, port):
        try:
            self.forward.connect((host, port))
            print("Forward", [host, port], "connected")
            return self.forward
        except Exception as e:
            print(e)
            return False

class Proxy:

    input_list = []
    channel = {}

    def __init__(self, proxy_manager, host, ports):
        self.servers = []
        for port in ports:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((host, port))
            server.listen(200)
            self.servers.append(server)
        self.proxy_manager = proxy_manager
        self.proxyAuthentication = False

    def setAuth(self, username, password):
        self.proxyAuthentication = True
        self.auth = Authenticate(username, password)

    def main_loop(self):
        self.input_list.extend(self.servers)
        while 1:
            time.sleep(delay)
            ss = select.select
            inputready, outputready, exceptready = ss(self.input_list, [], [])
            for self.s in inputready:
                if self.s in self.servers:
                    self.on_accept()
                    break

                try:
                    self.data = self.s.recv(buffer_size)
                    if len(self.data) == 0:
                        self.on_close()
                        break
                    else:
                        self.on_recv()

                except Exception as e:
                    print(e)
                    self.on_close()
                    break

    def on_accept(self):
        clientsock, clientaddr = self.s.accept()

        authenticated = not self.proxyAuthentication
        if not authenticated:
            authenticated = self.auth.authenticate(clientsock, clientaddr)
        else:
            print("Connecting client", clientaddr, "without authentication")

        if authenticated:
            protocol = self.detect_protocol(clientsock)
            forward_host, forward_port, proxy_type = self.proxy_manager.get_proxy(self.s.getsockname()[1], protocol)
            forward = Forward().start(forward_host, forward_port)
            if forward:
                print("Client", clientaddr, "connected")
                self.input_list.append(clientsock)
                self.input_list.append(forward)
                self.channel[clientsock] = forward
                self.channel[forward] = clientsock
            else:
                print("Can't establish connection with remote server")
                print("Closing connection with client", clientaddr)
                clientsock.close()
        else:
            print("Client", clientaddr, "not authenticated")
            print("Rejecting connection from", clientaddr)
            self.send_401_response(clientsock)
            clientsock.close()

    def on_close(self):
        try:
            print(self.s.getpeername(), "disconnected")
        except Exception as e:
            print(e)
            print("Client closed")

        self.input_list.remove(self.s)
        self.input_list.remove(self.channel[self.s])
        out = self.channel[self.s]
        self.channel[out].close()  # equivalent to do self.s.close()
        self.channel[self.s].close()
        del self.channel[out]
        del self.channel[self.s]

    def on_recv(self):
        data = self.data
        # print data
        self.channel[self.s].send(data)

    def detect_protocol(self, clientsock):
        """
        Detect whether the protocol is HTTP or HTTPS based on the initial request.
        """
        try:
            initial_data = clientsock.recv(buffer_size, socket.MSG_PEEK)
            if initial_data.startswith(b'CONNECT'):
                return 'https'
            else:
                return 'http'
        except Exception as e:
            print(f"Error detecting protocol: {e}")
            return 'http'

    def send_401_response(self, clientsock):
        """
        Sends a 401 Unauthorized response to the client.
        """
        response = b"HTTP/1.1 401 Unauthorized\r\n"
        response += b"Proxy-Authenticate: Basic realm=\"User Visible Realm\"\r\n"
        response += b"Content-Type: text/html\r\n"
        response += b"Content-Length: 0\r\n"
        response += b"Connection: close\r\n\r\n"
        clientsock.sendall(response)