import json,tempfile,unittest
from pathlib import Path
from threading import Thread
from urllib.request import urlopen,Request
from urllib.error import HTTPError
from app import connect,enqueue,work,finish_job,claim_job
from dashboard import create_dashboard,snapshot
class DashboardTests(unittest.TestCase):
    def test_snapshot_excludes_payload_and_exposes_transitions(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'queue.sqlite3';db=connect(path);enqueue(db,'secret-job',{'token':'never expose'},now=1);work(db,now=2);db.close();data=snapshot(path)
            self.assertEqual(data['stats']['completed'],1);self.assertNotIn('payload',data['jobs'][0]);self.assertEqual(data['events'][0]['kind'],'completed')
    def test_loopback_dashboard_serves_assets_and_api(self):
        with tempfile.TemporaryDirectory() as root:
            server=create_dashboard(Path(root)/'queue.sqlite3',0);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                with urlopen(f'http://127.0.0.1:{server.server_port}/') as response:self.assertIn(b'Queue Lab',response.read())
                with urlopen(f'http://127.0.0.1:{server.server_port}/api/snapshot') as response:self.assertEqual(json.load(response)['stats']['jobs'],0)
            finally:server.shutdown();server.server_close();thread.join()
    def test_replay_control_requires_token_and_confirmation(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'queue.sqlite3';db=connect(path);job=enqueue(db,'dead',{'handler':'fail','message':'x'},max_attempts=1,now=1);claim=claim_job(db,'w',now=2);finish_job(db,claim,'w',error='failed',now=3);db.close()
            server=create_dashboard(path,0,control_token='test-token');thread=Thread(target=server.serve_forever,daemon=True);thread.start();url=f'http://127.0.0.1:{server.server_port}/api/replay'
            try:
                with self.assertRaises(HTTPError) as denied:urlopen(Request(url,data=b'{"job_id":1,"confirm":"REPLAY"}',method='POST'))
                self.assertEqual(denied.exception.code,403)
                request=Request(url,data=json.dumps({'job_id':job,'confirm':'REPLAY'}).encode(),method='POST',headers={'X-Queue-Token':'test-token','Content-Type':'application/json'})
                with urlopen(request) as response:self.assertEqual(json.load(response)['state'],'pending')
            finally:server.shutdown();server.server_close();thread.join()
