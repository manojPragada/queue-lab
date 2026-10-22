import json,tempfile,unittest
from pathlib import Path
from threading import Thread
from urllib.request import urlopen
from app import connect,enqueue,work
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
