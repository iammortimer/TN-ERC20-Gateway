import sqlite3 as sqlite

alterTableExecuted = '''
    ALTER TABLE executed
    ADD COLUMN timestamp text;
'''

alterTableExecuted2 = '''
    ALTER TABLE executed
    ADD COLUMN amount real;
'''

alterTableExecuted3 = '''
    ALTER TABLE executed
    ADD COLUMN amountFee real;
'''

con = sqlite.connect('gateway.db')
cursor = con.cursor()
cursor.execute(alterTableExecuted)
cursor.execute(alterTableExecuted2)
cursor.execute(alterTableExecuted3)
con.commit()
con.close()