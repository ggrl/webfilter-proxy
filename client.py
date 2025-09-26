import socket


client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


client_socket.connect(('localhost', 8080))

request = """GET / HTTP/1.1
Host: httpbin.org
User-Agent: SimplePythonClient

"""

client_socket.send(request.encode())

response = client_socket.recv(4096).decode()
print("Response received:")
print(response)

client_socket.close()