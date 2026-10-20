import unittest
from app import connect, enqueue, work, job_result, replay_dead


class HandlerTests(unittest.TestCase):
    def setUp(self):
        self.db = connect(':memory:')

    def tearDown(self):
        self.db.close()

    def test_uppercase_persists_result(self):
        job = enqueue(self.db, 'text', {'handler': 'uppercase', 'text': 'Hello café'})
        work(self.db, now=1)
        self.assertEqual(job_result(self.db, job)['result'], {'text': 'HELLO CAFÉ'})
        self.assertEqual(job_result(self.db, job)['state'], 'completed')

    def test_unknown_handler_retries_without_evaluating_code(self):
        job = enqueue(self.db, 'bad', {'handler': '__import__("os")'}, max_attempts=2, retry_delay=0)
        self.assertEqual(work(self.db, now=1)['state'], 'pending')
        self.assertEqual(work(self.db, now=2)['state'], 'dead')
        self.assertEqual(job_result(self.db, job)['last_error'], 'unknown_handler')
        replay_dead(self.db, job, now=3)
        self.assertIsNone(job_result(self.db, job)['last_error'])

    def test_invalid_and_oversized_text_is_failed(self):
        for i, text in enumerate([None, 42, 'x' * 10001]):
            job = enqueue(self.db, str(i), {'handler': 'uppercase', 'text': text}, max_attempts=1)
            work(self.db, now=1)
            self.assertEqual(job_result(self.db, job)['last_error'], 'invalid_text')

    def test_old_payloads_keep_noop_behavior(self):
        for i, payload in enumerate([{}, ['data'], None]):
            job = enqueue(self.db, str(i), payload)
            work(self.db, now=1)
            self.assertEqual(job_result(self.db, job)['state'], 'completed')
            self.assertIsNone(job_result(self.db, job)['result'])

    def test_missing_and_invalid_job_results(self):
        for value in [0, True, '1', 999]:
            with self.assertRaises(ValueError):
                job_result(self.db, value)

    def test_non_json_numbers_rejected_before_enqueue(self):
        with self.assertRaises(ValueError):
            enqueue(self.db, 'bad', {'value': float('nan')})
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0], 0)

    def test_cli_result_survives_process_restart(self):
        import json
        import subprocess
        import sys
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            command = [sys.executable, 'app.py', '--db', str(Path(directory) / 'queue.sqlite3')]
            for args in [['enqueue', 'greeting', '{"handler":"uppercase","text":"hello"}'], ['work']]:
                subprocess.run(command + args, check=True, capture_output=True, text=True)
            result = subprocess.run(command + ['result', '1'], check=True, capture_output=True, text=True)
            self.assertEqual(json.loads(result.stdout)['result'], {'text': 'HELLO'})
