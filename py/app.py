#run it:
#./uwsgi -s /tmp/web.py.socket -w testapp
import web
import json
import parse_pto 
import os

PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
PTO_DIR = os.path.join(PROJECT_ROOT, 'pto')
IMG_DIR = os.path.join(PROJECT_ROOT, 'img')

urls = (
    '/load/(.*)', 'load',
    '/list', 'list',
#    '/upload', 'upload',
)

app = web.application(urls, globals())

def load_pto(filename):
    file = open(filename, 'r')
    pto = parse_pto.pto_scan(file)
    return pto

class list:
    def GET(self):
        x = os.walk(PTO_DIR).next()
        filelist = x[2]
        ptolist = [file for file in filelist if os.path.splitext(file)[1].lower() == '.pto' ]
        return json.dumps(ptolist)

class load:
    def GET(self, filename):
        if '/' in filename or filename.startswith('.'):
            raise ValueError("Illegal character in filename")
        pto = load_pto(os.path.join(PTO_DIR, filename))
        pto_data = []
        for i in pto.i:
            pto_data.append({ 
                          'name': i.n.value,
                          'yaw': i.y.value,
                          'pitch': i.p.value,
                          'roll': i.r.value,
                          'view': i.v.value,
                        })
        return json.dumps(pto_data) 

#application = app.wsgifunc()

web.webapi.internalerror = web.debugerror
if __name__ == "__main__": app.run()
