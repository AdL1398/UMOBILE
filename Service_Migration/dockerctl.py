#!/usr/bin/env python2.7

import time
import subprocess
import thread
import urllib
from docker import Client
from docker.utils import create_host_config

client = Client(base_url='unix://var/run/docker.sock',version='auto')
pulling_flag = False

def run_image(image_name, port_host, port_container):
    print time.strftime("%a, %d %b %Y %X +0000", time.gmtime())
    if has_image(image_name) == True:
        config = create_host_config(port_bindings={port_container:port_host})
        container = client.create_container(image=image_name, ports=[port_container], host_config=config)
        client.start(container=container.get('Id'))
        print time.strftime("%a, %d %b %Y %X +0000", time.gmtime())
        return is_image_running(image_name)
    print time.strftime("%a, %d %b %Y %X +0000", time.gmtime())
    return False

def has_image(image_name):
    local_images = client.images()
    for image in local_images:
        if image_name in image["RepoTags"]:
            return True
    return False

def pull_image(repo, image_name, wait=True):
    print time.strftime("%a, %d %b %Y %X +0000", time.gmtime())
    if repo == None: #pull from docker hub
        print 'Pulling image %s from default repo ...' % image_name
        client.pull(image_name, stream=True)
    else:
        print 'Pulling image %s from %s ...' % [image_name, repo]
        client.pull(repo, image_name, stream=True)
    if wait == True:
        timeout = 32
        timeout_step = 1
        while (has_image(image_name) == False and timeout_step <= timeout):
            print 'Waiting %d seconds ...' % timeout_step
            time.sleep(timeout_step)
            timeout_step *= 2
        if timeout_step > timeout:
            print 'Pulling timed out'
        else:
            print 'Pulling finished'
    print time.strftime("%a, %d %b %Y %X +0000", time.gmtime())
    return has_image(image_name)

def is_image_running(image_name):
    for container in client.containers():
        if container["Image"] == image_name:
            return True
    return False

def pull_tar_image(image_name, url, wait):
    print 'pulling tar image'
    global pulling_flag
    if pulling_flag == True:
        return False
    if (wait == True):
        pull_tar_image_helper(image_name, url)
        pulling_flag=False
        return has_image(image_name)
    else:
        thread.start_new_thread(pull_tar_image_helper,(image_name, url))
        return False

def pull_tar_image_helper(image_name, url):
    print 'pulling tar image helper'
    print time.strftime("%a, %d %b %Y %X +0000", time.gmtime())
    global pulling_flag
    image_shortname = image_name[image_name.find("/")+1:image_name.find(":")]
    #subprocess.check_call(["wget", "-O", image_shortname+'.tar', url])
    # for k in range(20):
    #     print 'loading image = %d' % k
    #     time.sleep(1)
    #print time.strftime("%a, %d %b %Y %X +0000", time.gmtime())
    pulling_flag=True
    testfile = urllib.URLopener()
    #testfile.retrieve(url, image_shortname+'.tar',reporthook)
    testfile.retrieve(url, image_shortname+'.tar')
    print 'pulling finish'
    print time.strftime("%a, %d %b %Y %X +0000", time.gmtime())
    print image_shortname+'.tar'
    #subprocess.check_call(["docker", "load", "-i",image_shortname+'.tar'])
    #client.load_image('/proxy/'+image_shortname+'.tar')
    f = open('./'+image_shortname+'.tar', 'r')
    client.load_image(f)
    pulling_flag=False
    print 'image loaded'

def reporthook(a,b,c):
    print "%d: %d: %d:" % (a,b,c)
