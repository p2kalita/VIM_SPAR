import sqlite3
import os

BASEDIR = os.path.abspath(os.path.dirname(__file__))

db_path = os.path.join(BASEDIR, "instance", "vim_database.sqlite")

print("Looking for:", os.path.abspath(db_path))
print("Exists:", os.path.exists(db_path))

conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
print("Tables:", cur.fetchall())

cur.execute("SELECT * FROM user;")
print("Users:", cur.fetchall())

conn.close()