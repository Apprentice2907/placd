import sqlite3
db = sqlite3.connect('d:/Job Searcher/Placd/backend/placd.db')
print([row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()])
