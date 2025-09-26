import socketserver
import select
import socket
from urllib.parse import urlparse



class ProxyRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        while True:  # loop until client disconnects
            try:
                # --- Read request headers ---
                request_data_bin = b""
                while True:
                    chunk = self.request.recv(4096)
                    if not chunk:
                        return  # client closed connection
                    request_data_bin += chunk
                    if b"\r\n\r\n" in request_data_bin:
                        break

                # --- Split headers and maybe partial body ---
                header_part, _, body_part = request_data_bin.partition(b"\r\n\r\n")
                headers = header_part.decode("utf-8", errors="ignore").splitlines()

                # --- Check for Content-Length ---
                content_length = 0
                for line in headers:
                    if line.lower().startswith("content-length:"):
                        content_length = int(line.split(":", 1)[1].strip())
                        break

                # --- Read full body if needed ---
                remaining = content_length - len(body_part)
                while remaining > 0:
                    chunk = self.request.recv(min(4096, remaining))
                    if not chunk:
                        break
                    body_part += chunk
                    remaining -= len(chunk)

                # --- Rebuild full request ---
                full_request = header_part + b"\r\n\r\n" + body_part
                request_text = full_request.decode("utf-8", errors="ignore")
                if not request_text:
                    return

                # --- First request line ---
                first_line = request_text.splitlines()[0]
                print(f"Request line: {first_line}")

                # --- HTTPS CONNECT handling ---
                if first_line.startswith("CONNECT"):
                    host_port = first_line.split(" ")[1]
                    if ":" in host_port:
                        host, port = host_port.split(":")
                        port = int(port)
                    else:
                        host, port = host_port, 443

                    if self.black_listed(host):
                        print(f"BLOCKED HTTPS: {host}")
                        return

                    try:
                        target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        target_socket.connect((host, port))
                        self.request.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
                        self.tunnel_data(self.request, target_socket)
                    except Exception as e:
                        print(f"HTTPS tunnel error: {e}")
                    return  # tunnel takes over, so stop loop

                # --- Extract Host header ---
                host = None
                for line in request_text.splitlines():
                    if line.lower().startswith("host:"):
                        host = line.split(":", 1)[1].strip()
                        break

                if self.black_listed(host):
                    print(f"BLOCKED: Access to {host} is forbidden")
                    return

                if host:
                    target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    target_socket.connect((host, 80))
                    self.http_request(self.request, target_socket, full_request)
                else:
                    print("No host header found")
                    return

                print("Response returned (ready for next request if any)")

            except Exception as e:
                print(f"Error in handle loop: {e}")
                return

    def black_listed(self, host):
        blacklist = ("facebook.com", "x.com", "httpbin.org")
        if host.startswith("http://"):
            host = urlparse(host).hostname
        else:
            host = "//" + host
            host = urlparse(host).hostname
        #print(host)
        for url in blacklist:
            x = 0
            if url.startswith("http://"):
                url2 = urlparse(url)
            else:
                url = "//" + url
                url2 = urlparse(url)
            url3 = url2.hostname
            #print(url3)
            if host == url3 or host.endswith('.' + url3):
                return True
        return False 
    
    
    def http_request(self, client_socket, server_socket, full_request):
        try:
            # Send the request once
            server_socket.sendall(full_request)

            # Read the response
            response = b""
            while True:
                chunk = server_socket.recv(4096)
                if not chunk:
                    break
                response += chunk
                # Optional: stop early if Content-Length is reached or chunked end detected

            # Send response back to client
            client_socket.sendall(response)

        except Exception as e:
            print(f"HTTP request error: {e}")

        finally:
            try:
                client_socket.close()
                server_socket.close()
            except:
                pass

    def tunnel_data(self, client_socket, server_socket, passed_data=b''):
        sockets = [client_socket, server_socket]
        if passed_data:
            server_socket.sendall(passed_data)
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