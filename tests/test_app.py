import unittest
import tempfile
from pathlib import Path
from app import connect,enqueue,work,replay_dead
class Tests(unittest.TestCase):
    def setUp(self):self.db=connect(':memory:')
    def tearDown(self):self.db.close()
    def test_idempotency(self):
        first=enqueue(self.db,'a',{'x':1});self.assertEqual(first,enqueue(self.db,'a',{'x':1}))
        with self.assertRaises(ValueError):enqueue(self.db,'a',{'x':2})
    def test_success(self):
        enqueue(self.db,'a',{});self.assertEqual(work(self.db)['state'],'completed');self.assertIsNone(work(self.db))
    def test_dead_letter(self):
        enqueue(self.db,'a',{'demo_fail':True},2,retry_delay=0)
        self.assertEqual(work(self.db)['state'],'pending');self.assertEqual(work(self.db)['state'],'dead');self.assertIsNone(work(self.db))
    def test_persistence(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'q.sqlite3';a=connect(path);enqueue(a,'a',{});a.close()
            b=connect(path)
            try:self.assertEqual(work(b)['state'],'completed')
            finally:b.close()


    def test_scheduled_retry_and_exponential_backoff(self):
        enqueue(self.db,'fail',{'demo_fail':True},4,retry_delay=2)
        self.assertEqual(work(self.db,now=100)['available_at'],102)
        self.assertIsNone(work(self.db,now=101))
        self.assertEqual(work(self.db,now=102)['available_at'],106)
        self.assertIsNone(work(self.db,now=105))
        self.assertEqual(work(self.db,now=106)['available_at'],114)
    def test_delayed_job_does_not_block_other_jobs(self):
        enqueue(self.db,'fail',{'demo_fail':True},3,retry_delay=2)
        work(self.db,now=100);second=enqueue(self.db,'ok',{})
        self.assertEqual(work(self.db,now=100)['id'],second)
    def test_dead_replay_preserves_id_and_resets_attempts(self):
        job=enqueue(self.db,'a',{'demo_fail':True},1);work(self.db,now=1)
        self.assertEqual(replay_dead(self.db,job,now=10)['attempts'],0)
        self.assertIsNone(work(self.db,now=9));self.assertEqual(work(self.db,now=10)['state'],'dead')
        with self.assertRaises(ValueError):replay_dead(self.db,999,now=10)
    def test_old_database_is_migrated_without_losing_jobs(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'old.sqlite3';db=sqlite3.connect(path)
            db.execute('CREATE TABLE jobs (id INTEGER PRIMARY KEY,key TEXT UNIQUE NOT NULL,payload TEXT NOT NULL,state TEXT NOT NULL,attempts INTEGER NOT NULL,max_attempts INTEGER NOT NULL)')
            db.execute('INSERT INTO jobs VALUES (1,"legacy","{}","pending",0,3)');db.commit();db.close()
            migrated=connect(path)
            try:self.assertEqual(work(migrated,now=1)['id'],1)
            finally:migrated.close()
    def test_invalid_retry_delay_and_live_replay_rejected(self):
        for value in [-1,float('nan'),float('inf'),True,3601]:
            with self.assertRaises(ValueError):enqueue(self.db,'bad',{},retry_delay=value)
        job=enqueue(self.db,'ok',{})
        with self.assertRaises(ValueError):replay_dead(self.db,job,now=1)
