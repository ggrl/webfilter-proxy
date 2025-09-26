import socketserver
import select
import socket
from urllib.parse import urlparse

class ProxyRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        
        request_data = self.request.recv(8192).decode("utf-8")
        if not request_data:
            return
        
        print(f"request: {request_data}")
        if not request_data:
            return
        host = None
        for line in request_data.split('\n'):
            if line.startswith('Host:'):
                host = line.split(' ')[1].strip()
                break
        if host:
            target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_socket.connect((host, 80))
            target_socket.send(request_data.encode())
            self.tunnel_data(self.request, target_socket)
            
        else:
            print("no host")    
        
        print("response returned")

        # YOUR CODE HERE:
        # 1. Parse the request to get the destination host and port.
        # 2. Connect to the destination server in a new socket.
        # 3. Send the initial request_data to that server.
        # 4. Call self.tunnel_data() to handle the rest of the communication.

    def tunnel_data(self, client_socket, server_socket):
        sockets = [client_socket, server_socket]
        print(f"client: {client_socket}, server: {server_socket}")
        while True:
            try:
                readable, _, exceptional = select.select(sockets, [], sockets, 60)
                if exceptional or not readable:
                    break
                for sock in readable:
                    data = sock.recv(4096)
                    if not data:
                        return

                    if sock is client_socket:
                        server_socket.sendall(data)
                    else:
                        client_socket.sendall(data)
                
                # YOUR CODE HERE:
                # Loop through the readable sockets. For each socket, receive the
                # data. If the data came from the client, send it to the server.
                # If it came from the server, send it to the client.
                # If you receive no data, the connection is closed, so you should exit.

            except Exception as e:
                print(f"Error: {e}")
                break
        client_socket.close()
        server_socket.close()        

if __name__ == "__main__":
    HOST, PORT = "127.0.0.1", 8080
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    server = socketserver.ThreadingTCPServer((HOST, PORT), ProxyRequestHandler)
    print(f"[*] Starting browser-ready proxy on port {PORT}")
    server.serve_forever()