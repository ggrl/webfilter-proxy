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
        for line in request_data.splitlines():
            if line.lower().startswith("host:"):
                host = line.split(":", 1)[1].strip()
                break
        if self.black_listed(host):
            print(f"BLOCKED: Access to {host} is forbidden")
            
            return
             
        if host:
            target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_socket.connect((host, 80))
            target_socket.send(request_data.encode())
            self.tunnel_data(self.request, target_socket)
            
        else:
            print("no host")    
        
        print("response returned")

    def black_listed(self, host):
        blacklist = ("facebook.com", "x.com", "httpbin.org")
        if host.startswith("http://"):
            host = urlparse(host).hostname
        else:
            host = "//" + host
            host = urlparse(host).hostname
        print(host)
        for url in blacklist:
            x = 0
            if url.startswith("http://"):
                url2 = urlparse(url)
            else:
                url = "//" + url
                url2 = urlparse(url)
            url3 = url2.hostname
            print(url3)
            if host in url3 or host.endswith('.' + url3):
                return True
        return False 


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
                
                

            except Exception as e:
                print(f"Error: {e}")
                break
        try:
            client_socket.close()
            server_socket.close()
        except:
            print("No sockets open")            

if __name__ == "__main__":
    HOST, PORT = "127.0.0.1", 8080
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    server = socketserver.ThreadingTCPServer((HOST, PORT), ProxyRequestHandler)
    print(f"[*] Starting browser-ready proxy on port {PORT}")
    server.serve_forever()