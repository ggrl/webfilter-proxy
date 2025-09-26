from urllib.parse import urlparse

urls = ("www.example.com", "http://x.com", "wowww.com", "http://x.main.net", "slashpage.de/index", "www.portpage.com:80", "http://2xend.co.uk")

while True:
    host = input(": ")
    #host = urlparse(host)
    if host.startswith("http://"):
            host = urlparse(host).hostname
            #print(url2.hostname)
    else:
            host = "//" + host
            host = urlparse(host).hostname
            #print(url2.hostname)
    print(host)
    for url in urls:
        x = 0
        if url.startswith("http://"):
            url2 = urlparse(url)
            #print(url2.hostname)
        else:
            url = "//" + url
            url2 = urlparse(url)
            #print(url2.hostname)
        url3 = url2.hostname#.split('.')[-2] + "." + url2.hostname.split('.')[-1]
        print(url3)
        if host == url3 or host.endswith('.' + url3):
            x = 1
            break
    if x == 0:
        print("fine...")
    else:
        print("####BLOCKED!!!!!!#####")            