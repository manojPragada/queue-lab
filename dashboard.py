"""Loopback-only, read-only queue dashboard."""
import json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from app import connect,queue_stats,event_history

ROOT=Path(__file__).with_name('dashboard')
ASSETS={'/':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8'),'/style.css':('style.css','text/css; charset=utf-8')}
def snapshot(database):
    db=connect(database)
    try:
        jobs=[dict(row) for row in db.execute('SELECT id,key,state,attempts,max_attempts,available_at,worker_id,lease_until,last_error FROM jobs ORDER BY id DESC LIMIT 100')]
        return {'stats':queue_stats(db),'jobs':jobs,'events':event_history(db,limit=50)}
    finally:db.close()
def create_dashboard(database,port=8765):
    if type(port) is not int or not 0<=port<=65535:raise ValueError('Port must be from 0 to 65535')
    database=str(Path(database).resolve())
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path=urlsplit(self.path).path
            if path=='/api/snapshot':
                body=json.dumps(snapshot(database),allow_nan=False).encode();kind='application/json; charset=utf-8'
            elif path in ASSETS:
                name,kind=ASSETS[path];body=(ROOT/name).read_bytes()
            else:self.send_error(404);return
            self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
        def log_message(self,*args):pass
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)
