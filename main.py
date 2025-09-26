import socket


proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
proxy_socket.bind(('localhost', 8080))
proxy_socket.listen(1)

print("Server started...")

while True:
    
    client_socket, client_address = proxy_socket.accept()
    print(f"Client connected: {client_address}")
    
    
    request = client_socket.recv(4096).decode()
    print(f"request: {request}")
    if not request:
        client_socket.close()
        continue
    host = None
    for line in request.split('\n'):
        if line.startswith('Host:'):
            host = line.split(' ')[1].strip()
            break
    
    
    #request = f"GET / HTTP/1.1\r\nHost: {host}\r\nUser-Agent: python-client\r\n\r\n"
    
    if host:
        target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target_socket.connect((host, 80))
        target_socket.send(request.encode())
        response = target_socket.recv(4096)
        
        client_socket.send(response)
        target_socket.close()
    else:
        print("no host")    
    
    client_socket.close()
    print("response returned")