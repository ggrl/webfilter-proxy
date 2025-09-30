import socketserver
import select
import socket
from urllib.parse import urlparse
import ssl
import threading
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
import os
import datetime
import time
import json

CA_CERT_FILE = "temporary_demo_cert.pem"  #Demo-cert create new one and insert here 
CA_KEY_FILE = "temporary_demo_key.pem"    #Demo-key: create new one and insert here
CERTS_DIR = "certs"       
os.makedirs(CERTS_DIR, exist_ok=True)

HOST, PORT = "127.0.0.1", 8080


_cert_lock = threading.Lock()


#load cert and key
def load_ca():
    with open(CA_CERT_FILE, "rb") as f:
        ca_cert_bytes = f.read()
    with open(CA_KEY_FILE, "rb") as f:
        ca_key_bytes = f.read()
    ca_cert = x509.load_pem_x509_certificate(ca_cert_bytes)
    ca_key = serialization.load_pem_private_key(ca_key_bytes, password=None)
    return ca_cert, ca_key

CA_CERT_OBJ, CA_KEY_OBJ = load_ca()


#create cer/key for host if it not exists yet
def generate_and_cache_cert(hostname: str):
    safe = hostname.replace(":", "_")
    cert_path = os.path.join(CERTS_DIR, f"{safe}.pem")
    key_path = os.path.join(CERTS_DIR, f"{safe}.key")

    if os.path.exists(cert_path) and os.path.exists(key_path):
        return cert_path, key_path

    
    with _cert_lock:
        if os.path.exists(cert_path) and os.path.exists(key_path):
            return cert_path, key_path

        #generate key
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, hostname)])
        now = datetime.datetime.utcnow()
        builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(CA_CERT_OBJ.subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=365))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName(hostname)]), critical=False)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        )

        cert = builder.sign(private_key=CA_KEY_OBJ, algorithm=hashes.SHA256())

        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )

        #write files
        tmp_cert = cert_path + ".tmp"
        tmp_key = key_path + ".tmp"
        with open(tmp_cert, "wb") as f:
            f.write(cert_pem)
        with open(tmp_key, "wb") as f:
            f.write(key_pem)
        os.replace(tmp_cert, cert_path)
        os.replace(tmp_key, key_path)

        return cert_path, key_path

class MITMProxyRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            #http or https?
            self.request.settimeout(10.0)
            data = self.request.recv(4096, socket.MSG_PEEK)
            if not data:
                return
            first_line = data.split(b'\r\n', 1)[0].decode('utf-8', errors='ignore')
            print(f"Request: {first_line}")

            if first_line.upper().startswith("CONNECT"):
                self._read_full_request()
                self.handle_https_connect(first_line)
            else:
                
                req = self._read_full_request()
                self.handle_http_request(req)
        except Exception as e:
            print(f"Error in handle: {e}")
            try:
                self.request.close()
            except:
                pass


    #Read until end of header - if content-length ->read body            
    def _read_full_request(self):    
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = self.request.recv(4096)
            if not chunk:
                break
            data += chunk
        if not data:
            return data

        header_part, _, body_part = data.partition(b"\r\n\r\n")
        headers = header_part.decode("utf-8", errors="ignore").splitlines()
        print(headers)
        content_length = 0
        for h in headers:
            if h.lower().startswith("content-length:"):
                try:
                    content_length = int(h.split(":", 1)[1].strip())
                except:
                    content_length = 0
                break
        remaining = content_length - len(body_part)
        while remaining > 0:
            chunk = self.request.recv(min(4096, remaining))
            if not chunk:
                break
            body_part += chunk
            remaining -= len(chunk)
        full = header_part + b"\r\n\r\n" + body_part
        return full


    def handle_https_connect(self, first_line_bytes_or_str):
        if isinstance(first_line_bytes_or_str, bytes):
            first_line = first_line_bytes_or_str.decode('utf-8', errors='ignore')
        else:
            first_line = first_line_bytes_or_str

        parts = first_line.split()
        if len(parts) < 2:
            return
        host_port = parts[1]
        if ":" in host_port:
            host, port = host_port.split(":")
            port = int(port)
        else:
            host, port = host_port, 443

        print(f"HTTPS connect for {host}:{port}")

        if self.black_listed(host):
            self.block_page(host)
            return

        #begin TLS 
        try:
            self.request.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
        except Exception as e:
            print("Failed to send 200:", e)
            return

    
        try:
            certfile, keyfile = generate_and_cache_cert(host)
        except Exception as e:
            print("Cert generation failed:", e)
            return

        
        try:
            server_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            server_ctx.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
            server_ctx.load_cert_chain(certfile=certfile, keyfile=keyfile)
        except Exception as e:
            print("Failed to create server SSL context:", e)
            return

        #wrap client into TLS
        try:
            client_tls = server_ctx.wrap_socket(self.request, server_side=True, do_handshake_on_connect=True)
        except Exception as e:
            print("Client TLS handshake failed:", e)
            try: self.request.close()
            except: pass
            return

        
        upstream_tls = None
        upstream_methods = []
        try:
            upstream_tls, method = self._establish_upstream_tls(host, port)
            if upstream_tls is None:
                print("Could not establish upstream TLS; closing")
                try: client_tls.close()
                except: pass
                return
        except Exception as e:
            print("Upstream TLS establishment error:", e)
            try:
                client_tls.close()
            except:
                pass
            return

        
        try:
            self._proxy_bidirectional(client_tls, upstream_tls)
        finally:
            self.safe_close(client_tls)
            self.safe_close(upstream_tls)


    #Try default, then certifi (most consistent) or fallback to system default (unsecure)
    def _establish_upstream_tls(self, host, port, timeout=10):

        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            ctx = ssl.create_default_context()
            upstream = ctx.wrap_socket(sock, server_hostname=host)
            print("system default working")
            return upstream, "system"
        except Exception as e:
            try: sock.close()
            except: pass
            print("system default failed", repr(e))

        
        try:
            import certifi
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            ctx = ssl.create_default_context(cafile=certifi.where())
            upstream = ctx.wrap_socket(sock, server_hostname=host)
            print("certifi working")
            return upstream, "certifi"
        except Exception as e:
            try: sock.close()
            except: pass
            print("certifi failed - fallback to unverified", repr(e))

        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            upstream = ctx.wrap_socket(sock, server_hostname=host)
            print("unverified working (insecure)")
            return upstream, "insecure"
        except Exception as e:
            try: sock.close()
            except: pass
            print("unverified failed", repr(e))
            return None, None


    #bidirectional forwarding
    def _proxy_bidirectional(self, sock_a, sock_b, timeout=60):
        last_activity = time.time()
        sockets = [sock_a, sock_b]
        while True:
            try:
                readable, _, exceptional = select.select(sockets, [], sockets, 1.0)
            except Exception as e:
                print("select error in proxy:", e)
                break

            if exceptional:
                break

            now = time.time()
            if now - last_activity > timeout:
                break

            if not readable:
                continue

            for s in readable:
                try:
                    data = s.recv(65536)
                except ssl.SSLWantReadError:
                    continue
                except ssl.SSLWantWriteError:
                    continue
                except Exception as e:
                    
                    #print("recv error:", e)
                    return

                if not data:
                    return

                last_activity = now

                
                dest = sock_b if s is sock_a else sock_a
                
                #with open("data/mitm.log", "a") as f: #logging everything
                    #f.write(data.decode("utf-8"))
                sent = False
                while not sent:
                    try:
                        dest.sendall(data)
                        sent = True
                    except ssl.SSLWantWriteError:
                        continue
                    except Exception as e:
                        
                        #print("send error:", e)
                        return

    def handle_http_request(self, full_request_bytes):
        try:
            
            header_part, _, body = full_request_bytes.partition(b"\r\n\r\n")
            headers = header_part.decode("utf-8", errors="ignore").splitlines()
            host = None
            for h in headers:
                if h.lower().startswith("host:"):
                    host = h.split(":", 1)[1].strip()
                    break
            if not host:
                print("No host")
                return
            if self.black_listed(host):
                self.block_page(host)
                return

            
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.settimeout(10)
            server_sock.connect((host, 80))

            
            server_sock.sendall(full_request_bytes)

            
            self._proxy_bidirectional(self.request, server_sock)
        except Exception as e:
            print("HTTP handling error:", e)
        finally:
            try:
                server_sock.close()
            except:
                pass



    def black_listed(self, host):
        blacklist = ()
        with open("data/blacklist.json", "r", encoding="utf-8") as f:
            blacklist = json.load(f)
            for i in range(0,len(blacklist)):
                blacklist[i] = blacklist[i].strip()
        print(blacklist)
        
        
        if not host:
            return False
        
        host = host.split(":", 1)[0].lower()
        for blocked in blacklist:
            if host == blocked or host.endswith("." + blocked):
                return True
        return False




    def block_page(self, host):
        try:
            print(f"BLOCKED: {host}")

            # load template from file
            try:
                with open("data/blocked.html", "r", encoding="utf-8") as f:
                    blocked_html = f.read()
            except FileNotFoundError:
                blocked_html = """<html><head><title>Blocked</title></head>
                <body><h1>Access Blocked</h1><p>Access has been blocked by the proxy.</p></body></html>"""

            # allow template variable substitution
            blocked_html = blocked_html.replace("{host}", host)

            body = blocked_html.encode("utf-8")
            headers = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/html; charset=utf-8\r\n"
                f"Content-Length: {len(body)}\r\n"
                "Connection: close\r\n"
                "\r\n"
            ).encode("utf-8")

            self.request.sendall(headers + body)

        except Exception as e:
            print("Error sending block page:", e)
        finally:
            self.safe_close(self.request)



    def safe_close(self, s):
        try:
            if hasattr(s, "shutdown"):
                try:
                    s.shutdown(socket.SHUT_RDWR)
                except:
                    pass
        except:
            pass
        try:
            s.close()
        except:
            pass

if __name__ == "__main__":
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    server = socketserver.ThreadingTCPServer((HOST, PORT), MITMProxyRequestHandler)
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    print(f"[*] Starting proxy on {HOST}:{PORT}")
    server.serve_forever()