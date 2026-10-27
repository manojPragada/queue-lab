import tempfile,unittest
from app import connect,enqueue,claim_job,worker_leases
class WorkerLeaseTests(unittest.TestCase):
 def test_groups_only_active_leases_without_payloads(self):
  with tempfile.NamedTemporaryFile() as file:
   db=connect(file.name);enqueue(db,'a',{'secret':'hidden'},now=0);enqueue(db,'b',{},now=0);claim_job(db,'worker-b',10,now=1);claim_job(db,'worker-a',20,now=1)
   rows=worker_leases(db,now=2);self.assertEqual([row['worker_id'] for row in rows],['worker-a','worker-b']);self.assertTrue(all('payload' not in row for row in rows));self.assertEqual(worker_leases(db,now=30),[]);db.close()
