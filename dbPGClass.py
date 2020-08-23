import psycopg2 as pgdb
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from datetime import timedelta
import datetime
import os

class dbPGCalls(object):
    def __init__(self, config):
        self.config = config

        try:
            self.dbCon = pgdb.connect(database=config['main']['name'], user=self.config["postgres"]["pguser"], password=self.config["postgres"]["pgpswd"], host=self.config["postgres"]["pghost"], port=self.config["postgres"]["pgport"])
            self.dbCon.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        except:
            self.dbCon = pgdb.connect(user=self.config["postgres"]["pguser"], password=self.config["postgres"]["pgpswd"], host=self.config["postgres"]["pghost"], port=self.config["postgres"]["pgport"])
            self.dbCon.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            sqlstr = sql.SQL('CREATE DATABASE {};').format(sql.Identifier(self.config['main']['name']))
            cursor = self.dbCon.cursor()
            cursor.execute(sqlstr)
            cursor.close()
            self.dbCon.close()
            self.dbCon = pgdb.connect(database=config['main']['name'], user=self.config["postgres"]["pguser"], password=self.config["postgres"]["pgpswd"], host=self.config["postgres"]["pghost"], port=self.config["postgres"]["pgport"])
            self.dbCon.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

#DB Setup part
    def createdb(self):
        createHeightTable = '''
            CREATE TABLE IF NOT EXISTS heights (
                id SERIAL PRIMARY KEY,
                chain text NOT NULL,
                height integer
            );
        '''
        createTunnelTable = '''
            CREATE TABLE IF NOT EXISTS tunnel (
                id SERIAL PRIMARY KEY,
                sourceaddress text NOT NULL,
                targetaddress text NOT NULL,
                timestamp timestamp
                default current_timestamp,
                status text
            );
        '''
        createTableExecuted = '''
            CREATE TABLE IF NOT EXISTS executed (
                id SERIAL PRIMARY KEY,
                sourceaddress text NOT NULL,
                targetaddress text NOT NULL,
                tntxid text NOT NULL,
                ethtxid text NOT NULL,
                timestamp timestamp
                default current_timestamp,
                amount real,
                amountFee real
        );
        '''
        createTableErrors = '''
            CREATE TABLE IF NOT EXISTS errors (
                id SERIAL PRIMARY KEY,
                sourceaddress text ,
                targetaddress text ,
                tntxid text ,
                ethtxid text ,
                timestamp timestamp
                default current_timestamp,
                amount real,
                error text,
                exception text
        );
        '''
        createVerifyTable = '''
            CREATE TABLE IF NOT EXISTS verified (
                id SERIAL PRIMARY KEY,
                chain text NOT NULL,
                tx text NOT NULL,
                block integer
            );
        '''

        cursor = self.dbCon.cursor()
        cursor.execute(sql.SQL(createHeightTable))
        cursor.execute(sql.SQL(createTunnelTable))
        cursor.execute(sql.SQL(createTableExecuted))
        cursor.execute(sql.SQL(createTableErrors))
        cursor.execute(sql.SQL(createVerifyTable))

#import existing sqlite db
    def importSQLite(self):
        import sqlite3

        if self.config["main"]["db-location"] != "":
            path= os.getcwd()
            dbfile = path + '\\' + self.config["main"]["db-location"] + '\\' + 'gateway.db'
            dbfile = os.path.normpath(dbfile)
        else:
            dbfile = 'gateway.db'

        consq=sqlite3.connect(dbfile)
        cursq=consq.cursor()
        
        tabnames=[]
        
        cursq.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tabgrab = cursq.fetchall()
        for item in tabgrab:
            tabnames.append(item[0])
        
        for table in tabnames:
            cursq.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name = ?;", (table,))
            create = cursq.fetchone()[0]
            cursq.execute("SELECT * FROM %s;" %table)
            rows=cursq.fetchall()
            colcount=len(rows[0])
            pholder='%s,'*colcount
            newholder=pholder[:-1]
        
            try:
                curpg = self.dbCon.cursor()
                curpg.execute("DROP TABLE IF EXISTS %s;" %table)
                curpg.execute(create)
                curpg.executemany("INSERT INTO %s VALUES (%s);" % (table, newholder),rows)
        
            except pgdb.DatabaseError as e:
                print ('Error %s' % e) 

            if table != 'heights':
                curpg.execute("ALTER TABLE %s ALTER id ADD GENERATED ALWAYS AS IDENTITY (START WITH %s);" % (table, len(rows)+1))
        
        consq.close()

#heights table related
    def lastScannedBlock(self, chain):
        sql = 'SELECT height FROM heights WHERE chain = %s'
        values = (chain,)

        cursor = self.dbCon.cursor()
        cursor.execute(sql, values)
        qryResult = cursor.fetchall()
        cursor.close()

        if len(qryResult) > 0:
            return qryResult[0][0]
        else:
            return {}

    def getHeights(self):
        sql = 'SELECT chain, height FROM heights'

        cursor = self.dbCon.cursor()
        cursor.execute(sql)
        qryResult = cursor.fetchall()
        cursor.close()

        if len(qryResult) > 0:
            return qryResult
        else:
            return {}

    def updHeights(self, block, chain):
        sql = 'UPDATE heights SET "height" = %s WHERE chain = %s'
        values = (block, chain)

        cursor = self.dbCon.cursor()
        cursor.execute(sql, values)
        cursor.close()

    def insHeights(self, block, chain):
        sql = 'INSERT INTO heights ("chain", "height") VALUES (%s, %s)'
        values = (chain, block)

        cursor = self.dbCon.cursor()
        cursor.execute(sql, values)
        cursor.close()

#tunnel table related
    def doWeHaveTunnels(self):
        sql = 'SELECT * FROM tunnel WHERE status = "created"'

        cursor = self.dbCon.cursor()
        cursor.execute(sql)
        qryResult = cursor.fetchall()
        cursor.close()

        if len(qryResult) > 0:
            return True
        else:
            return False

    def gettargetaddress(self, sourceaddress):
        sql = 'SELECT targetaddress FROM tunnel WHERE status <> "error" AND sourceaddress = %s'
        values = (sourceaddress,)

        cursor = self.dbCon.cursor()
        cursor.execute(sql, values)
        qryResult = cursor.fetchall()
        cursor.close()

        if len(qryResult) > 0:
            return qryResult[0][0]
        else:
            return {}

    def getsourceaddress(self, targetaddress):
        sql = 'SELECT sourceaddress FROM tunnel WHERE status <> "error" AND targetaddress = %s'
        values = (targetaddress,)

        cursor = self.dbCon.cursor()
        cursor.execute(sql, values)
        qryResult = cursor.fetchall()
        cursor.close()

        if len(qryResult) > 0:
            return qryResult[0][0]
        else:
            return {}

    def getTunnelStatus(self, targetaddress = '', sourceaddress = ''):
        if targetaddress != '':
            sql = 'SELECT status FROM tunnel WHERE targetaddress = %s ORDER BY id DESC LIMIT 1'
            values = (targetaddress,)
        elif  sourceaddress != '':
            sql = 'SELECT status FROM tunnel WHERE sourceaddress = %s ORDER BY id DESC LIMIT 1'
            values = (sourceaddress,)
        else:
            return {}

        cursor = self.dbCon.cursor()
        cursor.execute(sql, values)
        qryResult = cursor.fetchall()
        cursor.close()

        if len(qryResult) > 0:
            return qryResult
        else:
            return {}

    def getTunnels(self, status = ''):
        if status != '':
            sql = 'SELECT sourceaddress, targetaddress FROM tunnel WHERE status = %s'
            values = (status,)
        else:
            return {}

        cursor = self.dbCon.cursor()
        cursor.execute(sql, values)
        qryResult = cursor.fetchall()
        cursor.close()

        if len(qryResult) > 0:
            return qryResult
        else:
            return {}

    def insTunnel(self, status, sourceaddress, targetaddress):
        sql = 'INSERT INTO tunnel ("sourceaddress", "targetaddress", "status", "timestamp") VALUES (%s, %s, %s, CURRENT_TIMESTAMP)'
        values = (sourceaddress, targetaddress, status)

        cursor = self.dbCon.cursor()
        cursor.execute(sql, values)
        cursor.close()

    def updTunnel(self, status, sourceaddress, targetaddress, statusOld = ''):
        if statusOld == '':
            statusOld = 'created'

        sql = 'UPDATE tunnel SET "status" = %s, "timestamp" = CURRENT_TIMESTAMP WHERE status = %s AND sourceaddress = %s and targetaddress = %s'
        values = (status, statusOld, sourceaddress, targetaddress)

        cursor = self.dbCon.cursor()
        cursor.execute(sql, values)
        cursor.close()

    def delTunnel(self, sourceaddress, targetaddress):
        sql = 'DELETE FROM tunnel WHERE sourceaddress = %s and targetaddress = %s'
        values = (sourceaddress, targetaddress)

        cursor = self.dbCon.cursor()
        cursor.execute(sql, values)
        cursor.close()

#executed table related
    def insExecuted(self, sourceaddress, targetaddress, ethtxid, tntxid, amount, amountFee):
        sql = 'INSERT INTO executed ("sourceaddress", "targetaddress", "ethtxid", "tntxid", "amount", "amountFee") VALUES (%s, %s, %s, %s, %s, %s)'
        values = (sourceaddress, targetaddress, ethtxid, tntxid, amount, amountFee)

        cursor = self.dbCon.cursor()
        cursor.execute(sql, values)
        cursor.close()

    def updExecuted(self, id, sourceaddress, targetaddress, ethtxid, tntxid, amount, amountFee):
        sql = 'UPDATE executed SET "sourceaddress" = %s, "targetaddress" = %s, "ethtxid" = %s, "tntxid" = %s, "amount" = %s, "amountFee" = %s) WHERE id = %s'
        values = (sourceaddress, targetaddress, ethtxid, tntxid, amount, amountFee, id)

        cursor = self.dbCon.cursor()
        cursor.execute(sql, values)
        cursor.close()

    def didWeSendTx(self, txid):
        sql = 'SELECT * FROM executed WHERE (ethtxid = %s OR tntxid = %s)'
        values = (txid, txid)

        cursor = self.dbCon.cursor()
        cursor.execute(sql, values)
        qryResult = cursor.fetchall()
        cursor.close()

        if len(qryResult) > 0:
            return True
        else:
            return False

    def getExecutedAll(self):
        sql = 'SELECT * FROM executed'

        cursor = self.dbCon.cursor()
        cursor.execute(sql)
        qryResult = cursor.fetchall()
        cursor.close()

        if len(qryResult) > 0:
            return qryResult
        else:
            return {}

    def getExecuted(self, sourceaddress = '', targetaddress = '', ethtxid = '', tntxid = ''):
        if sourceaddress != '':
            sql = 'SELECT ethtxid FROM executed WHERE sourceaddress = %s ORDER BY id DESC LIMIT 1'
            values = (sourceaddress,)
        elif targetaddress != '':
            sql = 'SELECT tntxid FROM executed WHERE targetaddress = %s ORDER BY id DESC LIMIT 1'
            values = (targetaddress,)
        elif ethtxid != '':
            sql = 'SELECT * FROM executed WHERE ethtxid = %s ORDER BY id DESC LIMIT 1'
            values = (ethtxid,)
        elif tntxid != '':
            sql = 'SELECT * FROM executed WHERE tntxid = %s ORDER BY id DESC LIMIT 1'
            values = (tntxid,)
        else:
            return {}

        cursor = self.dbCon.cursor()
        cursor.execute(sql, values)
        qryResult = cursor.fetchall()
        cursor.close()

        if len(qryResult) > 0:
            return qryResult
        else:
            return {}

#error table related
    def insError(self, sourceaddress, targetaddress, tntxid, ethtxid, amount, error, exception = ''):
        sql = 'INSERT INTO errors ("sourceaddress", "targetaddress", "tntxid", "ethtxid", "amount", "error", "exception") VALUES (%s, %s, %s, %s, %s, %s, %s)'
        values = (sourceaddress, targetaddress, tntxid, ethtxid, amount, error, exception)

        cursor = self.dbCon.cursor()
        cursor.execute(sql, values)
        cursor.close()

    def getErrors(self):
        sql = 'SELECT * FROM errors'

        cursor = self.dbCon.cursor()
        cursor.execute(sql)
        qryResult = cursor.fetchall()
        cursor.close()

        if len(qryResult) > 0:
            return qryResult
        else:
            return {}

    def getError(self, sourceaddress='', targetaddress=''):
        if sourceaddress != '':
            sql = 'SELECT error, tntxid, ethtxid FROM errors WHERE sourceaddress = %s ORDER BY id DESC LIMIT 1'
            values = (sourceaddress,)
        elif targetaddress != '':
            sql = 'SELECT error, tntxid, ethtxid FROM errors WHERE targetaddress = %s ORDER BY id DESC LIMIT 1'
            values = (targetaddress,)
        else:
            return {}

        cursor = self.dbCon.cursor()
        cursor.execute(sql, values)
        qryResult = cursor.fetchall()
        cursor.close()

        if len(qryResult) > 0:
            return qryResult
        else:
            return {}

#verified table related
    def getVerifiedAll(self):
        sql = 'SELECT * FROM verified'

        cursor = self.dbCon.cursor()
        cursor.execute(sql)
        qryResult = cursor.fetchall()
        cursor.close()

        if len(qryResult) > 0:
            return qryResult
        else:
            return {}

    def getUnVerified(self):
        sql = 'SELECT * FROM verified WHERE block = 0'

        cursor = self.dbCon.cursor()
        cursor.execute(sql)
        qryResult = cursor.fetchall()
        cursor.close()

        if len(qryResult) > 0:
            return qryResult
        else:
            return {}

    def getVerified(self, tx):
        sql = 'SELECT block FROM verified WHERE tx = %s'
        values = (tx,)

        cursor = self.dbCon.cursor()
        cursor.execute(sql, values)
        qryResult = cursor.fetchall()
        cursor.close()

        if len(qryResult) > 0:
            return qryResult[0][0]
        else:
            return None

    def insVerified(self, chain, tx, block):
        if self.getVerified(tx) is None:
            sql = 'INSERT INTO verified ("chain", "tx", "block") VALUES (%s, %s, %s)'
            values = (chain, tx, block)

            cursor = self.dbCon.cursor()
            cursor.execute(sql, values)
            cursor.close()
        else:
            sql = 'UPDATE verified SET "block" = %s WHERE tx = %s'
            values = (block, tx)

            cursor = self.dbCon.cursor()
            cursor.execute(sql, values)
            cursor.close()

#other
    def checkTXs(self, address):
        if address == '':
            cursor = self.dbCon.cursor()
            sql = "SELECT e.sourceaddress, e.targetaddress, e.tntxid, e.ethtxid as 'OtherTxId', ifnull(v.block, 0) as 'TNVerBlock', ifnull(v2.block, 0) as 'OtherVerBlock', e.amount, CASE WHEN e.targetaddress LIKE '3J%' THEN 'Deposit' ELSE 'Withdraw' END 'TypeTX', " \
            "CASE WHEN e.targetaddress LIKE '3J%' AND v.block IS NOT NULL THEN 'verified' WHEN e.targetaddress NOT LIKE '3J%' AND v2.block IS NOT NULL AND v2.block IS NOT 0 THEN 'verified' ELSE 'unverified' END 'Status' " \
            "FROM executed e LEFT JOIN verified v ON e.tntxid = v.tx LEFT JOIN verified v2 ON e.ethtxid = v2.tx "
            cursor.execute(sql)
        else:
            cursor = self.dbCon.cursor()
            sql = "SELECT e.sourceaddress, e.targetaddress, e.tntxid, e.ethtxid as 'OtherTxId', ifnull(v.block, 0) as 'TNVerBlock', ifnull(v2.block, 0) as 'OtherVerBlock', e.amount, CASE WHEN e.targetaddress LIKE '3J%' THEN 'Deposit' ELSE 'Withdraw' END 'TypeTX', " \
            "CASE WHEN e.targetaddress LIKE '3J%' AND v.block IS NOT NULL THEN 'verified' WHEN e.targetaddress NOT LIKE '3J%' AND v2.block IS NOT NULL AND v2.block IS NOT 0 THEN 'verified' ELSE 'unverified' END 'Status' " \
            "FROM executed e LEFT JOIN verified v ON e.tntxid = v.tx LEFT JOIN verified v2 ON e.ethtxid = v2.tx WHERE (e.sourceaddress = %s or e.targetaddress = %s)"
            cursor.execute(sql, (address, address))

        tx = [dict((cursor.description[i][0], value) for i, value in enumerate(row)) for row in cursor.fetchall()]
        cursor.close()

        if len(tx) == 0:
            return {'error': 'no tx found'}
        else:
            return tx

    def getFees(self, fromdate, todate):
        #check date notation
        if len(fromdate) != 0:
            fromyear,frommonth,fromday = fromdate.split('-')

            isValidFromDate = True
            try :
                datetime.datetime(int(fromyear),int(frommonth),int(fromday))
            except ValueError :
                isValidFromDate = False
        else:
            isValidFromDate = False

        if len(todate) != 0:
            toyear,tomonth,today = todate.split('-')

            isValidtoDate = True
            try :
                datetime.datetime(int(toyear),int(tomonth),int(today))
            except ValueError :
                isValidtoDate = False
        else:
            isValidtoDate = False

        if not isValidFromDate:
            fromdate = '1990-01-01'
    
        if not isValidtoDate:
            todat = datetime.date.today() + timedelta(days=1)
            todate = todat.strftime('%Y-%m-%d')
        
        values = (fromdate, todate)

        sql = 'SELECT SUM(amountFee) as totalFee from executed WHERE timestamp > %s and timestamp < %s'

        cursor = self.dbCon.cursor()
        cursor.execute(sql, values)
        qryResult = cursor.fetchall()
        cursor.close()

        if len(qryResult) == 0:
            Fees = 0
        else:
            Fees = qryResult[0][0]

        return { 'totalFees': Fees }