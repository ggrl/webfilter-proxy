## webfilter proxy and mitm-proxy

### a cybersteps project

This application is a working webfilter proxy.

### How to use

#### normal proxy

The 'proxy.py' is a proxy, which forwards http-requests and -responses and also forwards encrypted traffic for secure https-connections.
For webfiltering: Start 'settings.py', open '127.0.0.1:42000' in your browser to edit the filtering options.

Configure your browser to a proxy at 127.0.0.1:8080.

Start 'proxy.py'

#### mitm proxy

The 'mitm-proxy.py' is a proxy, which decrypts https-traffic. It has also the ability to log requests and responses.

To use it, you have to generate a private key and certification with this key. You can do that with OpenSSL.

You need to install the generated certification in your browser, move the key and cert in your application folder and rename the variables in your code (line 16 and 17):

```python
CA_CERT_FILE = "demo_cert.pem"  #Demo-cert create new one and insert here 
CA_KEY_FILE = "demo_key.pem"    #Demo-key: create new one and insert here
```
Every request and response is logged into 'mitm.log'. To disable logging change the variable 'logx' in line 24.

```python
logx = True #Enables/disables logging
```

For webfiltering: Start 'settings.py', open '127.0.0.1:42000' in your browser to edit the filtering options.

Configure your browser to a proxy at 127.0.0.1:8080.

Start 'mitm-proxy.py'

## IMPORTANT:
### The included "demo_cert.pem" and "demo_key.pem" are for testing-purposes only. Do not use them outside a secure lab-security


