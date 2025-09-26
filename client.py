import socket


client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(('localhost', 8080))
input_request = input("Enter website: ")
request = f"GET / HTTP/1.1\r\nHost: {input_request}\r\nUser-Agent: python-client\r\n\r\n"
client_socket.send(request.encode())

response = client_socket.recv(4096).decode()
print("response:")
print(response)

client_socket.close()