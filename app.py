"""Persistent single-worker job queue demonstration using SQLite."""
import argparse
import json
import math
import time
import sqlite3
import sys

def connect(path):
    db=sqlite3.connect(path);db.row_factory=sqlite3.Row
    db.execute('CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY, key TEXT UNIQUE NOT NULL, payload TEXT NOT NULL, state TEXT NOT NULL DEFAULT "pending", attempts INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL)');db.commit()
    columns = {row['name'] for row in db.execute('PRAGMA table_info(jobs)')}
    with db:
        if 'available_at' not in columns:
            db.execute('ALTER TABLE jobs ADD COLUMN available_at REAL NOT NULL DEFAULT 0')
        if 'retry_delay' not in columns:
            db.execute('ALTER TABLE jobs ADD COLUMN retry_delay REAL NOT NULL DEFAULT 1')
    return db

def nonnegative(value, name):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError(name + ' must be finite and non-negative')
    return value

def enqueue(db,key,payload,max_attempts=3,retry_delay=1):
    if not key or type(max_attempts) is not int or max_attempts<1:raise ValueError('Non-empty key and positive max_attempts required')
    nonnegative(retry_delay, 'retry_delay')
    if retry_delay > 3600:raise ValueError('retry_delay must not exceed 3600 seconds')
    encoded=json.dumps(payload)
    with db:
        row=db.execute('SELECT * FROM jobs WHERE key=?',(key,)).fetchone()
        if row:
            if json.loads(row['payload'])!=payload or row['max_attempts']!=max_attempts or row['retry_delay']!=retry_delay:raise ValueError('Idempotency key already used with different input')
            return row['id']
        return db.execute('INSERT INTO jobs (key,payload,max_attempts,retry_delay) VALUES (?,?,?,?)',(key,encoded,max_attempts,retry_delay)).lastrowid

def replay_dead(db, job_id, now=None):
    timestamp = nonnegative(time.time() if now is None else now, 'now')
    with db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT state FROM jobs WHERE id=?', (job_id,)).fetchone()
        if row is None or row['state'] != 'dead':
            raise ValueError('Replay requires an existing dead-letter job')
        db.execute('UPDATE jobs SET state="pending", attempts=0, available_at=? WHERE id=?', (timestamp, job_id))
    return {'id': job_id, 'state': 'pending', 'attempts': 0, 'available_at': timestamp}

def work(db, now=None):
    timestamp = nonnegative(time.time() if now is None else now, 'now')
    # Entire demo handler is transactional. Not for long-running external jobs.
    with db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT * FROM jobs WHERE state="pending" AND available_at<=? ORDER BY available_at,id LIMIT 1',(timestamp,)).fetchone()
        if not row:return None
        payload=json.loads(row['payload']);attempt=row['attempts']+1
        fail=isinstance(payload,dict) and payload.get('demo_fail') is True
        state=('dead' if attempt>=row['max_attempts'] else 'pending') if fail else 'completed'
        ready = timestamp + min(3600, row['retry_delay'] * 2 ** min(attempt-1, 12)) if fail and state == 'pending' else 0
        db.execute('UPDATE jobs SET attempts=?,state=?,available_at=? WHERE id=?',(attempt,state,ready,row['id']))
        return {'id':row['id'],'attempts':attempt,'state':state,'available_at':ready}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',default='queue.sqlite3');sub=p.add_subparsers(dest='command',required=True)
    e=sub.add_parser('enqueue');e.add_argument('key');e.add_argument('payload');e.add_argument('--max-attempts',type=int,default=3);e.add_argument('--retry-delay',type=float,default=1)
    sub.add_parser('work');sub.add_parser('list');r=sub.add_parser('replay');r.add_argument('job_id',type=int);a=p.parse_args()
    try:
        db=connect(a.db)
        try:
            if a.command=='enqueue':result={'id':enqueue(db,a.key,json.loads(a.payload),a.max_attempts,a.retry_delay)}
            elif a.command=='work':result=work(db)
            elif a.command=='replay':result=replay_dead(db,a.job_id)
            else:result=[dict(row) for row in db.execute('SELECT id,key,state,attempts,max_attempts,available_at,retry_delay FROM jobs ORDER BY id')]
            print(json.dumps(result,indent=2));return 0
        finally:db.close()
    except (OSError,ValueError,sqlite3.Error) as exc:print(str(exc),file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())

