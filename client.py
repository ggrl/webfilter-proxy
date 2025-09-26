import socket


client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(('localhost', 8080))
request = input("Enter website: ")

client_socket.send(request.encode())

response = client_socket.recv(4096).decode()
print("response:")
print(response)

client_socket.close()