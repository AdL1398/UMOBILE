#!/usr/bin/env python2.7

from threading import Thread
import SocketServer
import socket
import time
import sys
import socket
import dockerctl
import redisdb

proxy_port = 8000
docker_repo = None

class service(SocketServer.BaseRequestHandler):
    def handle(self):
        data = 'dummy'
        print "Client connected from ", self.client_address
        # Assume that the max size of http request is 8192
        data = self.request.recv(8192)
        #print data
        print time.strftime("%a, %d %b %Y %X +0000", time.gmtime())
        process_request(self.request, data)

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

def check_is_port_open(host_ip,container_port):
    timetostart=10
    timetostart_step=0
    result=1
    while (result!=0 and timetostart_step <= timetostart):
        time.sleep(1)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((host_ip,container_port))
        sock.close()
        timetostart_step += 1
    return result

def process_request(s, data):
    first_line = data.split('\n')[0]
    url = first_line.split(' ')[1]
    http_pos = url.find("://")
    if (http_pos == -1):
        temp = url
    else:
        temp = url[(http_pos+3):]

    port_pos = temp.find(":")
    webserver_pos = temp.find("/")
    if (webserver_pos == -1):
        webserver_pos = len(temp)
    webserver = ""
    port = -1
    if (port_pos == -1 or webserver_pos < port_pos):
        port = 80
        webserver = temp[:webserver_pos]
    else:
        port = int((temp[(port_pos+1):])[:webserver_pos-port_pos-1])
        webserver = temp[:port_pos]

    print 'Client requests for %s:%d' % (webserver,port)
    if redisdb.exists(webserver) == True:
        print "Found %s in db" % webserver
        docker_info = redisdb.get(webserver)
        docker_image_name = docker_info["image_name"]
        docker_tar_image_url = docker_info["tar_image_url"]
        docker_host = docker_info["hostname"]
        docker_port_host = docker_info["port_host"]
        docker_port_container = docker_info["port_container"]
        docker_container_status = docker_info["status"]
        if (docker_container_status == "running" and dockerctl.is_image_running(docker_image_name) == True):
            print 'Docker image %s is running' % docker_image_name
            forward_request(docker_host, docker_port_host, s, data)
        elif (docker_container_status == "offline" and dockerctl.is_image_running(docker_image_name) == False):
            print 'Docker image %s is not running' % docker_image_name
            if dockerctl.has_image(docker_image_name) == True:
                print 'Running docker image %s ...' % docker_image_name
                if dockerctl.run_image(docker_image_name, docker_port_host, docker_port_container) == True:
                    docker_info["status"] = "running"
                    redisdb.set(webserver, str(docker_info))  
                    if check_is_port_open(docker_host,docker_port_host) == 0:
                        print "Port is open"
                        forward_request(docker_host, docker_port_host, s, data)
                    else:
                        print "Port is not open"
                        forward_request(webserver, port, s, data)                                    
                else:
                    print 'Error: Cannot run image %s' % docker_image_name
                    forward_request(webserver, port, s, data)
            else:
                #print 'Pulling docker image %s ...' % docker_image_name
                #if dockerctl.pull_image(docker_repo, docker_image_name, wait=True) == True:
                print 'Pulling docker image %s from %s ...' % (docker_image_name,docker_tar_image_url)
                if dockerctl.pull_tar_image(docker_image_name, docker_tar_image_url, wait=False) == True:
                    print 'Pulling docker image %s completed. Running image ...' % docker_image_name
                    if dockerctl.run_image(docker_image_name, docker_port_host, docker_port_container) == True:
                        print 'Running docker image %s ...' % docker_image_name
                        docker_info["status"] = "running"
                        redisdb.set(webserver, str(docker_info))
                        if check_is_port_open(docker_host,docker_port_host) == 0:
                            print "Port is open"
                            forward_request(docker_host, docker_port_host, s, data)
                        else:
                            print "Port is not open"
                            forward_request(webserver, port, s, data)
                    else:
                        print 'Error: Cannot run image %s' % docker_image_name
                        forward_request(webserver, port, s, data)
                else:
                    print 'Error: Cannot pull image %s' % docker_image_name
                    forward_request(webserver, port, s, data)
        else:
            print 'Error: Unhandled status for image %s' % docker_image_name
            print 'Status =', docker_container_status
            print 'Image running =', dockerctl.is_image_running(docker_image_name)
            forward_request(webserver, port, s, data)
    else:
        print "Cannot find %s in db" % webserver
        forward_request(webserver, port, s, data)

def forward_request(webserver, port, s, data):
    print time.strftime("%a, %d %b %Y %X +0000", time.gmtime())
    print 'Forwarding request to %s:%d' % (webserver,port)
    forward_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    forward_socket.connect((webserver, port))
    print "Connected to %s" % webserver
    forward_socket.send(data)

    reply_chunk = 'dummy'
    reply = []
    reply_length = 0
    while len(reply_chunk):
        reply_chunk = forward_socket.recv(8192)
        print 'send chunk to user'
        reply.append(reply_chunk) # Waiting for complete contetn then send back to client (response time is large)
        complete_reply = ''.join(reply)
        for line in complete_reply.split('\n'):
            if 'Content-Length:' in line:
                reply_length = int(line[16:])
                break
        content = complete_reply.split('\r\n\r\n')
        if len(content)>=1 and sys.getsizeof(content[1]) >= reply_length:
            break

    forward_socket.close()
    print 'Forwarding reply back to client'
    s.send(complete_reply)
        #s.send(reply_chunk) ## continuous send packet --> have problem with other wensite i.e., cnn, bbs, these websites may use some scripts or special codes. Need to find other solotuons
    #forward_socket.close()
   
    print 'closing socket'
    s.close()
    print 'Connection closed'
    print time.strftime("%a, %d %b %Y %X +0000", time.gmtime())

def start_redis():
    if dockerctl.is_image_running("redis:latest") == True:
        print "Redis is already running"
    else:
        if dockerctl.has_image("redis:latest") == False:
            dockerctl.pull_image(None, "redis:latest", wait=True)
        dockerctl.run_image("redis:latest", 6379, 6379)
        print "Starting Redis ..."
        time.sleep(5)

def initialize():
    start_redis()
    #redisdb.set("www.cl.cam.ac.uk",'{"image_name":"al1309/web-site5mb:latest", "tar_image_url":"http://www.cl.cam.ac.uk/~al773/docker/web-site5mb.tar", "hostname":"192.168.1.104", "port_host":8080, "port_container":80,"status":"offline"}')
    redisdb.set("www.cl.cam.ac.uk",'{"image_name":"al1309/web-site500kb:latest", "tar_image_url":"http://www.cl.cam.ac.uk/~al773/docker/web-site500kb.tar", "hostname":"192.168.1.104", "port_host":8080, "port_container":80,"status":"offline"}')
    #redisdb.set("www.cl.cam.ac.uk",'{"image_name":"al1309/web-site5mb-mac:latest", "tar_image_url":"http://www.cl.cam.ac.uk/~al773/docker/web-site5mb-mac.tar", "hostname":"192.168.99.100", "port_host":8080, "port_container":80,"status":"offline"}')
    print "Initialization completed"

if __name__ == "__main__":
    initialize()
    t = ThreadedTCPServer(('',proxy_port), service)
    print 'Running at port', proxy_port
    t.serve_forever()
