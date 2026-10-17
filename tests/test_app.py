import unittest
import tempfile
from pathlib import Path
from app import connect,enqueue,work
class Tests(unittest.TestCase):
    def setUp(self):self.db=connect(':memory:')
    def tearDown(self):self.db.close()
    def test_idempotency(self):
        first=enqueue(self.db,'a',{'x':1});self.assertEqual(first,enqueue(self.db,'a',{'x':1}))
        with self.assertRaises(ValueError):enqueue(self.db,'a',{'x':2})
    def test_success(self):
        enqueue(self.db,'a',{});self.assertEqual(work(self.db)['state'],'completed');self.assertIsNone(work(self.db))
    def test_dead_letter(self):
        enqueue(self.db,'a',{'demo_fail':True},2)
        self.assertEqual(work(self.db)['state'],'pending');self.assertEqual(work(self.db)['state'],'dead');self.assertIsNone(work(self.db))
    def test_persistence(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'q.sqlite3';a=connect(path);enqueue(a,'a',{});a.close()
            b=connect(path)
            try:self.assertEqual(work(b)['state'],'completed')
            finally:b.close()
