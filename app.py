"""Persistent single-worker job queue demonstration using SQLite."""
import argparse
import json
import sqlite3
import sys

def connect(path):
    db=sqlite3.connect(path);db.row_factory=sqlite3.Row
    db.execute('CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY, key TEXT UNIQUE NOT NULL, payload TEXT NOT NULL, state TEXT NOT NULL DEFAULT "pending", attempts INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL)');db.commit();return db

def enqueue(db,key,payload,max_attempts=3):
    if not key or type(max_attempts) is not int or max_attempts<1:raise ValueError('Non-empty key and positive max_attempts required')
    encoded=json.dumps(payload)
    with db:
        row=db.execute('SELECT * FROM jobs WHERE key=?',(key,)).fetchone()
        if row:
            if json.loads(row['payload'])!=payload or row['max_attempts']!=max_attempts:raise ValueError('Idempotency key already used with different input')
            return row['id']
        return db.execute('INSERT INTO jobs (key,payload,max_attempts) VALUES (?,?,?)',(key,encoded,max_attempts)).lastrowid

def work(db):
    # Entire demo handler is transactional. Not for long-running external jobs.
    with db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT * FROM jobs WHERE state="pending" ORDER BY id LIMIT 1').fetchone()
        if not row:return None
        payload=json.loads(row['payload']);attempt=row['attempts']+1
        fail=isinstance(payload,dict) and payload.get('demo_fail') is True
        state=('dead' if attempt>=row['max_attempts'] else 'pending') if fail else 'completed'
        db.execute('UPDATE jobs SET attempts=?,state=? WHERE id=?',(attempt,state,row['id']))
        return {'id':row['id'],'attempts':attempt,'state':state}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',default='queue.sqlite3');sub=p.add_subparsers(dest='command',required=True)
    e=sub.add_parser('enqueue');e.add_argument('key');e.add_argument('payload');e.add_argument('--max-attempts',type=int,default=3)
    sub.add_parser('work');sub.add_parser('list');a=p.parse_args()
    try:
        db=connect(a.db)
        try:
            if a.command=='enqueue':result={'id':enqueue(db,a.key,json.loads(a.payload),a.max_attempts)}
            elif a.command=='work':result=work(db)
            else:result=[dict(row) for row in db.execute('SELECT id,key,state,attempts,max_attempts FROM jobs ORDER BY id')]
            print(json.dumps(result,indent=2));return 0
        finally:db.close()
    except (OSError,ValueError,sqlite3.Error) as exc:print(str(exc),file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
