"""Loopback-only, read-only queue dashboard."""
import json
import hmac
import secrets
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from app import connect,queue_stats,event_history,replay_dead

ROOT=Path(__file__).with_name('dashboard')
ASSETS={'/':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8'),'/style.css':('style.css','text/css; charset=utf-8')}
def snapshot(database):
    db=connect(database)
    try:
        jobs=[dict(row) for row in db.execute('SELECT id,key,state,attempts,max_attempts,available_at,worker_id,lease_until,last_error FROM jobs ORDER BY id DESC LIMIT 100')]
        return {'stats':queue_stats(db),'jobs':jobs,'events':event_history(db,limit=50)}
    finally:db.close()
def create_dashboard(database,port=8765,control_token=None):
    if type(port) is not int or not 0<=port<=65535:raise ValueError('Port must be from 0 to 65535')
    database=str(Path(database).resolve())
    token=control_token or secrets.token_urlsafe(24)
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path=urlsplit(self.path).path
            if path=='/api/snapshot':
                body=json.dumps(snapshot(database),allow_nan=False).encode();kind='application/json; charset=utf-8'
            elif path in ASSETS:
                name,kind=ASSETS[path];body=(ROOT/name).read_bytes()
            else:self.send_error(404);return
            self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
        def do_POST(self):
            if urlsplit(self.path).path!='/api/replay':self.send_error(404);return
            if not hmac.compare_digest(self.headers.get('X-Queue-Token',''),token):self.send_error(403);return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 1<=length<=4096:raise ValueError('Invalid request size')
                value=json.loads(self.rfile.read(length))
                if not isinstance(value,dict):raise ValueError('JSON object required')
                job_id=value.get('job_id')
                if value.get('confirm')!='REPLAY' or type(job_id) is not int:raise ValueError('Explicit replay confirmation required')
                db=connect(database)
                try:result=replay_dead(db,job_id)
                finally:db.close()
                body=json.dumps(result).encode();self.send_response(200)
            except (ValueError,json.JSONDecodeError) as error:
                body=json.dumps({'error':str(error)}).encode();self.send_response(400)
            self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler);server.control_token=token;return server
