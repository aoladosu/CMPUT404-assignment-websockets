#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2013-2014 Abram Hindle
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import flask
from flask import Flask, request
from flask_sockets import Sockets
import gevent
from gevent import queue
import time
import json
import os



app = Flask(__name__)
sockets = Sockets(app)
app.debug = True

clients = list()

class Client:
    def __init__(self):
        self.queue = queue.Queue()

    def put(self, v):
        self.queue.put_nowait(v)

    def get(self):
        return self.queue.get()


def send_all(msg):
    for client in clients:
        client.put( msg )

def send_all_json(obj):
    send_all( json.dumps(obj) )

class World:
    def __init__(self):
        self.clear()
        # we've got listeners now!
        self.listeners = list()
        
    def add_set_listener(self, listener):
        self.listeners.append( listener )

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        self.update_listeners( entity )

    def set(self, entity, data):
        self.space[entity] = data
       # self.queue.append(entity)

        #if (len(self.queue) >= 100):
        #    entity = self.queue.pop(0)
        #    self.space.pop(entity, [])

        self.update_listeners( entity )

    def update_listeners(self, entity):
        '''update the set listeners'''
        for listener in self.listeners:
            listener(entity, self.get(entity))

    def clear(self):
        self.space = dict()

    def get(self, entity):
        return self.space.get(entity,dict())
    
    def world(self):
        return self.space

myWorld = World()        

def set_listener( entity, data ):
    ''' do something with the update ! '''

myWorld.add_set_listener( set_listener )
        
@app.route("/")
def hello():
    '''Return something coherent here.. perhaps redirect to /static/index.html '''
    try:
        file = open("static/index.html", 'r')
        html = file.read()
        file.close()
    except:
        return '', 404
    return html, 200

@app.route("/json2.js")
def hi():
    try:
        file = open("static/json2.js", 'r')
        html = file.read()
        file.close()
    except:
        return '', 404
    return html, 200

def read_ws(ws, client):
    '''A greenlet function that reads from the websocket and updates the world'''
    # XXX: TODO IMPLEMENT ME
    try:
        while True:
            print("waiting for msg")
            msg = ws.receive()
            print("SERVER: WS RECV: %s" % msg)
            if (msg is not None):
                print("msg wasn't none")
                packet = json.loads(msg)
                print("json loaded")
                request = packet.get("world",None)
                print("request was:", request)
                if (request == "?"):
                    print("asked for world")
                    client.put(json.dumps(myWorld.world()))
                else:
                    print("didn't ask for world, setting world state")
                    for key in packet.keys():
                        myWorld.set(key, packet[key])
                    print("putting in the queue")    
                    for c in clients:
                        c.put(json.dumps(packet)) 
                    print("done")    
            else:
                break
    except Exception as e:
        print("erroring out:", e.args)
        pass

@sockets.route('/subscribe')
def subscribe_socket(ws):
    '''Fufill the websocket URL of /subscribe, every update notify the
       websocket and read updates from the websocket '''
    # XXX: TODO IMPLEMENT ME
    client = Client()
    clients.append(client)
    g = gevent.spawn( read_ws, ws, client)    
    try:
        while True:
            # block here
            print("hey new version")
            msg = client.get()
            ws.send(msg)
    except Exception as e:# WebSocketError as e:
        print("WS Error %s" % e)
    finally:
        pass
        clients.remove(client)
        gevent.kill(g)

# I give this to you, this is how you get the raw body/data portion of a post in flask
# this should come with flask but whatever, it's not my project.
def flask_post_json():
    '''Ah the joys of frameworks! They do so much work for you
       that they get in the way of sane operation!'''
    if (request.json != None):
        return request.json
    elif (request.data != None and request.data.decode("utf8") != u''):
        return json.loads(request.data.decode("utf8"))
    else:
        return json.loads(request.form.keys()[0])

@app.route("/entity/<entity>", methods=['POST','PUT'])
def update(entity):
    '''update the entities via this interface'''
    data = flask_post_json()
    myWorld.set(entity, data)
    return json.dumps(data), 200

@app.route("/world", methods=['POST','GET'])    
def world():
    return json.dumps(myWorld.world()), 200

@app.route("/entity/<entity>")    
def get_entity(entity):
    '''This is the GET version of the entity interface, return a representation of the entity'''
    return json.dumps(myWorld.get(entity)), 200


@app.route("/clear", methods=['POST','GET'])
def clear():
    myWorld.clear()
    return '', 200



if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''
    app.run()
