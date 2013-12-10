# -*- coding: utf-8 -*
__author__ = 'vitaliy'


from functools import partial
import threading
import tornado.httpserver
import tornado.websocket
import tornado.ioloop
import tornado.web
import redis
import json
import time
import datetime


LISTENERS = []
USERS = {
    '127.0.0.1' : 'Admin'
    ,'192.168.5.22' : 'Vitaliy'
    , '192.168.5.49' : 'Alex E.'
    , '192.168.5.69' : 'Pasha'
    , '192.168.5.40' : 'Serg P'
    , '192.168.5.105' : 'Serg D'
    , '192.168.5.19' : 'Serg D2'
    , '192.168.5.101' : 'Sasha A'
    , '192.168.5.27' : 'Yura'
}

def redis_listener():
    r = redis.Redis()
    #r = redis.StrictRedis(host='localhost', port=6379, db=0)
    ps = r.pubsub()
    ps.subscribe('test_realtime')
    io_loop = tornado.ioloop.IOLoop.instance()
    for message in ps.listen():
        for element in LISTENERS:
            io_loop.add_callback(partial(element.on_message, message))


class NewMsgHandler(tornado.web.RequestHandler):
    def get(self):
        if self.request.remote_ip in USERS.keys():
            file = open('index.html').read()
            result = file.replace("{{comments}}", self.getHistory())
        else:
            result = 'You have not permissions, your ip is: ' + self.request.remote_ip
            print(result)
        self.write(result)

    def post(self):
        r = redis.Redis()
        data = self.get_argument('data')
        name = USERS[self.request.remote_ip]
        date = time.strftime("%Y-%m-%d %H:%M:%S")
        comment = json.dumps({'user' : name, 'date' : date, 'message' : data})
        r.rpush('chat', comment)
        r.expire('chat', 86400)
        r.publish('test_realtime', comment)

    def getDate(self, date):
        currDate = time.strftime("%Y-%m-%d %H:%M:%S")
        if date[0:10] in currDate:
            return date[11:]
        else:
            return date[0:10]

    def getHistory(self):
        temp = ''
        r = redis.Redis()
        comments = r.lrange("chat", 0, -1)

        for comment_json in comments:
            comment = json.loads(comment_json)
            temp += '<tr class="history"><td>' + comment['user']\
                    + ' ('+self.getDate(comment['date'])+')</td>'\
                    + '<td>' + comment['message'] + '</td></tr>'
        return temp


class RealtimeHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        LISTENERS.append(self)
        self.online()

    def on_message(self, message):
        self.write_message(message['data'])

    def on_close(self):
        LISTENERS.remove(self)

    def online(self):
        users_online = ''
        for element in LISTENERS:
           users_online += USERS[element.request.remote_ip] + ', '

        data = json.dumps({'listteners' : users_online[0:-2]})
        try:
            self.write_message(data)
            tornado.ioloop.IOLoop.instance().add_timeout(datetime.timedelta(seconds=5), self.online)
        except AttributeError:
            pass

settings = {
    'auto_reload': True,
}

application = tornado.web.Application([
    (r'/', NewMsgHandler),
    (r'/realtime/', RealtimeHandler),
], **settings)


if __name__ == "__main__":
    threading.Thread(target=redis_listener).start()
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8888)
    tornado.ioloop.IOLoop.instance().start()