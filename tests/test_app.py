import unittest
import tempfile
from pathlib import Path
from app import connect,enqueue,work,replay_dead,queue_stats,event_history,claim_job,heartbeat,finish_job,set_queue_paused,drain_status
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


    def test_lifecycle_history_survives_replay(self):
        job=enqueue(self.db,'fail',{'demo_fail':True},1,now=1)
        work(self.db,now=2);replay_dead(self.db,job,now=3);work(self.db,now=4)
        self.assertEqual([e['kind'] for e in event_history(self.db,job)],['dead','claimed','replayed','dead','claimed','enqueued'])
        self.assertEqual(queue_stats(self.db,now=5)['recorded_failed_attempts'],2)
    def test_stats_distinguish_ready_and_delayed(self):
        enqueue(self.db,'fail',{'demo_fail':True},retry_delay=10,now=1);work(self.db,now=1)
        enqueue(self.db,'ok',{},now=2)
        stats=queue_stats(self.db,now=2)
        self.assertEqual((stats['pending'],stats['ready'],stats['delayed']),(2,1,1))
        self.assertEqual(queue_stats(self.db,now=11)['ready'],2)
    def test_idempotent_enqueue_does_not_duplicate_events(self):
        job=enqueue(self.db,'ok',{},now=1);enqueue(self.db,'ok',{},now=2)
        self.assertEqual(len(event_history(self.db,job)),1)
        with self.assertRaises(ValueError):event_history(self.db,limit=0)
    def test_legacy_jobs_do_not_get_fabricated_history(self):
        self.db.execute('INSERT INTO jobs (key,payload,state,attempts,max_attempts) VALUES ("legacy","{}","completed",2,3)');self.db.commit()
        stats=queue_stats(self.db,now=1)
        self.assertEqual(stats['completed'],1);self.assertEqual(stats['recorded_events'],0)

    def test_worker_lease_heartbeat_and_completion(self):
        job=enqueue(self.db,'leased',{'handler':'uppercase','text':'hello'},now=1)
        claim=claim_job(self.db,'worker-a',10,now=2);self.assertEqual((claim['id'],claim['lease_until']),(job,12))
        self.assertIsNone(claim_job(self.db,'worker-b',10,now=3));self.assertEqual(heartbeat(self.db,job,'worker-a',10,now=4)['lease_until'],14)
        self.assertEqual(finish_job(self.db,claim,'worker-a',{'text':'HELLO'},now=5)['state'],'completed')
        self.assertEqual([event['kind'] for event in event_history(self.db,job)],['completed','heartbeat','claimed','enqueued'])

    def test_expired_lease_is_recovered_by_another_worker(self):
        job=enqueue(self.db,'recover',{},max_attempts=2,now=1);claim_job(self.db,'gone',5,now=2)
        recovered=claim_job(self.db,'replacement',5,now=7);self.assertEqual((recovered['id'],recovered['attempts']),(job,2))
        with self.assertRaises(ValueError):heartbeat(self.db,job,'gone',now=7)
        self.assertIn('lease_expired',[event['kind'] for event in event_history(self.db,job)])

    def test_drain_status_requires_pause_and_no_active_leases(self):
        enqueue(self.db,'drain',{},now=1);claim_job(self.db,'worker',10,now=2);set_queue_paused(self.db,True)
        self.assertEqual(drain_status(self.db,now=3),{'paused':True,'running_leases':1,'latest_lease_until':12,'drained':False})
        self.assertTrue(drain_status(self.db,now=12)['drained'])

