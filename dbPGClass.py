import psycopg2 as pgdb
from psycopg2 import sql
from psycopg2 import pool
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from datetime import timedelta
import datetime
import os

class dbPGCalls(object):
    def __init__(self, config):
        self.config = config

        try:
            self.psPool = pgdb.pool.ThreadedConnectionPool(1, 10,database=config['main']['name'], user=self.config["postgres"]["pguser"], password=self.config["postgres"]["pgpswd"], host=self.config["postgres"]["pghost"], port=self.config["postgres"]["pgport"])
            dbCon = self.psPool.getconn()
            #self.dbCon = pgdb.connect(database=config['main']['name'], user=self.config["postgres"]["pguser"], password=self.config["postgres"]["pgpswd"], host=self.config["postgres"]["pghost"], port=self.config["postgres"]["pgport"])
            #self.dbCon.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            self.psPool.putconn(dbCon)
        except:
            self.dbCon = pgdb.connect(user=self.config["postgres"]["pguser"], password=self.config["postgres"]["pgpswd"], host=self.config["postgres"]["pghost"], port=self.config["postgres"]["pgport"])
            self.dbCon.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            sqlstr = sql.SQL('CREATE DATABASE {};').format(sql.Identifier(self.config['main']['name']))
            cursor = self.dbCon.cursor()
            cursor.execute(sqlstr)
            cursor.close()
            self.dbCon.close()

            self.psPool = pgdb.pool.ThreadedConnectionPool(1, 10,database=config['main']['name'], user=self.config["postgres"]["pguser"], password=self.config["postgres"]["pgpswd"], host=self.config["postgres"]["pghost"], port=self.config["postgres"]["pgport"])
            #self.dbCon = pgdb.connect(database=config['main']['name'], user=self.config["postgres"]["pguser"], password=self.config["postgres"]["pgpswd"], host=self.config["postgres"]["pghost"], port=self.config["postgres"]["pgport"])
            #self.dbCon.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    def openConn(self):
        dbCon = self.psPool.getconn()
        dbCon.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        return dbCon

    def closeConn(self, dbCon):
        self.psPool.putconn(dbCon)

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

        dbCon = self.openConn()
        cursor = dbCon.cursor()
        cursor.execute(sql.SQL(createHeightTable))
        cursor.execute(sql.SQL(createTunnelTable))
        cursor.execute(sql.SQL(createTableExecuted))
        cursor.execute(sql.SQL(createTableErrors))
        cursor.execute(sql.SQL(createVerifyTable))
        self.closeConn(dbCon)

#import existing sqlite db
    def importSQLite(self):
        import sqlite3

        if self.config["main"]["db-location"] != "":
            path= os.getcwd()
            dbfile = path + '/' + self.config["main"]["db-location"] + '/' + 'gateway.db'
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
        
        dbCon = self.openConn()
        for table in tabnames:
            cursq.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name = ?;", (table,))
            create = cursq.fetchone()[0]
            cursq.execute("SELECT * FROM %s;" %table)
            rows=cursq.fetchall()
            if len(rows) == 0:
                continue
            colcount=len(rows[0])
            pholder='%s,'*colcount
            newholder=pholder[:-1]
        
            try:
                curpg = dbCon.cursor()
                curpg.execute("DROP TABLE IF EXISTS %s;" %table)
                curpg.execute(create)
                curpg.executemany("INSERT INTO %s VALUES (%s);" % (table, newholder),rows)

                if table != 'heights':
                    curpg.execute("ALTER TABLE %s ALTER id ADD GENERATED ALWAYS AS IDENTITY (START WITH %s);" % (table, len(rows)+1))
        
            except Exception as e:
                self.closeConn(dbCon)
                print ('Error %s' % e) 
        
        self.closeConn(dbCon)
        consq.close()

#heights table related
    def lastScannedBlock(self, chain):
        sql = 'SELECT height FROM heights WHERE chain = %s'
        values = (chain,)

        dbCon = self.openConn()
        cursor = dbCon.cursor()
        cursor.execute(sql, values)
        qryResult = cursor.fetchall()
        cursor.close()
        self.closeConn(dbCon)

        if len(qryResult) > 0:
            return qryResult[0][0]
        else:
            return {}

    def getHeights(self):
        sql = 'SELECT chain, height FROM heights'

        dbCon = self.openConn()
        cursor = dbCon.cursor()
        cursor.execute(sql)
        qryResult = cursor.fetchall()
        cursor.close()
        self.closeConn(dbCon)

        if len(qryResult) > 0:
            return qryResult
        else:
            return {}

    def updHeights(self, block, chain):
        sql = 'UPDATE heights SET "height" = %s WHERE chain = %s'
        values = (block, chain)

        dbCon = self.openConn()
        cursor = dbCon.cursor()
        cursor.execute(sql, values)
        cursor.close()
        self.closeConn(dbCon)

    def insHeights(self, block, chain):
        sql = 'INSERT INTO heights ("chain", "height") VALUES (%s, %s)'
        values = (chain, block)

        dbCon = self.openConn()
        cursor = dbCon.cursor()
        cursor.execute(sql, values)
        cursor.close()
        self.closeConn(dbCon)

#tunnel table related
    def doWeHaveTunnels(self):
        sql = 'SELECT * FROM tunnel WHERE "status" = %s'
        values = ("created", )

        dbCon = self.openConn()
        cursor = dbCon.cursor()
        cursor.execute(sql, values)
        qryResult = cursor.fetchall()
        cursor.close()
        self.closeConn(dbCon)

        if len(qryResult) > 0:
            return True
        else:
            return False

    def getTargetAddress(self, sourceAddress):
        sql = 'SELECT targetaddress FROM tunnel WHERE "status" <> %s AND sourceaddress = %s'
        values = ("error", sourceAddress)

        dbCon = self.openConn()
        cursor = dbCon.cursor()
        cursor.execute(sql, values)
        qryResult = cursor.fetchall()
        cursor.close()
        self.closeConn(dbCon)

        if len(qryResult) > 0:
            return qryResult[0][0]
        else:
            return {}

    def getSourceAddress(self, targetAddress):
        sql = 'SELECT sourceaddress FROM tunnel WHERE "status" <> %s AND targetaddress = %s'
        values = ("error", targetAddress)

        dbCon = self.openConn()
        cursor = dbCon.cursor()
        cursor.execute(sql, values)
        qryResult = cursor.fetchall()
        cursor.close()
        self.closeConn(dbCon)

        if len(qryResult) > 0:
            return qryResult[0][0]
        else:
            return {}

    def getTunnelStatus(self, targetAddress = '', sourceAddress = ''):
        if targetAddress != '':
            sql = 'SELECT status FROM tunnel WHERE targetaddress = %s ORDER BY id DESC LIMIT 1'
            values = (targetAddress,)
        elif  sourceAddress != '':
            sql = 'SELECT status FROM tunnel WHERE sourceaddress = %s ORDER BY id DESC LIMIT 1'
            values = (sourceAddress,)
        else:
            return {}

        dbCon = self.openConn()
        cursor = dbCon.cursor()
        cursor.execute(sql, values)
        qryResult = cursor.fetchall()
        cursor.close()
        self.closeConn(dbCon)

        if len(qryResult) > 0:
            return qryResult
        else:
            return {}

    def getTunnels(self, status = ''):
        if status != '':
            sql = 'SELECT sourceaddress, targetaddress FROM tunnel WHERE "status" = %s'
            values = (status,)
        else:
            return {}

        dbCon = self.openConn()
        cursor = dbCon.cursor()
        cursor.execute(sql, values)
        qryResult = cursor.fetchall()
        cursor.close()
        self.closeConn(dbCon)

        if len(qryResult) > 0:
            return qryResult
        else:
            return {}

    def insTunnel(self, status, sourceAddress, targetAddress):
        sql = 'INSERT INTO tunnel ("sourceaddress", "targetaddress", "status", "timestamp") VALUES (%s, %s, %s, CURRENT_TIMESTAMP)'
        values = (sourceAddress, targetAddress, status)

        dbCon = self.openConn()
        cursor = dbCon.cursor()
        cursor.execute(sql, values)
        cursor.close()
        self.closeConn(dbCon)

    def updTunnel(self, status, sourceAddress, targetAddress, statusOld = ''):
        if statusOld == '':
            statusOld = 'created'

        sql = 'UPDATE tunnel SET "status" = %s, "timestamp" = CURRENT_TIMESTAMP WHERE status = %s AND sourceaddress = %s and targetaddress = %s'
        values = (status, statusOld, sourceAddress, targetAddress)

        dbCon = self.openConn()
        cursor = dbCon.cursor()
        cursor.execute(sql, values)
        cursor.close()
        self.closeConn(dbCon)

    def delTunnel(self, sourceAddress, targetAddress):
        sql = 'DELETE FROM tunnel WHERE sourceaddress = %s and targetaddress = %s'
        values = (sourceAddress, targetAddress)

        dbCon = self.openConn()
        cursor = dbCon.cursor()
        cursor.execute(sql, values)
        cursor.close()
        self.closeConn(dbCon)

#executed table related
    def insExecuted(self, sourceAddress, targetAddress, ethtxid, tntxid, amount, amountFee):
        sql = 'INSERT INTO executed ("sourceaddress", "targetaddress", "ethtxid", "tntxid", "amount", "amountfee") VALUES (%s, %s, %s, %s, %s, %s)'
        values = (sourceAddress, targetAddress, ethtxid, tntxid, amount, amountFee)

        dbCon = self.openConn()
        cursor = dbCon.cursor()
        cursor.execute(sql, values)
        cursor.close()
        self.closeConn(dbCon)

    def updExecuted(self, id, sourceAddress, targetAddress, ethtxid, tntxid, amount, amountFee):
        sql = 'UPDATE executed SET "sourceaddress" = %s, "targetaddress" = %s, "ethtxid" = %s, "tntxid" = %s, "amount" = %s, "amountfee" = %s) WHERE id = %s'
        values = (sourceAddress, targetAddress, ethtxid, tntxid, amount, amountFee, id)

        dbCon = self.openConn()
        cursor = dbCon.cursor()
        cursor.execute(sql, values)
        cursor.close()
        self.closeConn(dbCon)

    def didWeSendTx(self, txid):
        sql = 'SELECT * FROM executed WHERE (ethtxid = %s OR tntxid = %s)'
        values = (txid, txid)

        dbCon = self.openConn()
        cursor = dbCon.cursor()
        cursor.execute(sql, values)
        qryResult = cursor.fetchall()
        cursor.close()
        self.closeConn(dbCon)

        if len(qryResult) > 0:
            return True
        else:
            return False

    def getExecutedAll(self):
        sql = 'SELECT * FROM executed'

        dbCon = self.openConn()
        cursor = dbCon.cursor()
        cursor.execute(sql)
        qryResult = cursor.fetchall()
        cursor.close()
        self.closeConn(dbCon)

        if len(qryResult) > 0:
            return qryResult
        else:
            return {}

    def getExecuted(self, sourceAddress = '', targetAddress = '', ethtxid = '', tntxid = ''):
        if sourceAddress != '':
            sql = 'SELECT ethtxid FROM executed WHERE sourceaddress = %s ORDER BY id DESC LIMIT 1'
            values = (sourceAddress,)
        elif targetAddress != '':
            sql = 'SELECT tntxid FROM executed WHERE targetaddress = %s ORDER BY id DESC LIMIT 1'
            values = (targetAddress,)
        elif ethtxid != '':
            sql = 'SELECT * FROM executed WHERE ethtxid = %s ORDER BY id DESC LIMIT 1'
            values = (ethtxid,)
        elif tntxid != '':
            sql = 'SELECT * FROM executed WHERE tntxid = %s ORDER BY id DESC LIMIT 1'
            values = (tntxid,)
        else:
            return {}

        dbCon = self.openConn()
        cursor = dbCon.cursor()
        cursor.execute(sql, values)
        qryResult = cursor.fetchall()
        cursor.close()
        self.closeConn(dbCon)

        if len(qryResult) > 0:
            return qryResult
        else:
            return {}

#error table related
    def insError(self, sourceAddress, targetAddress, tntxid, ethtxid, amount, error, exception = ''):
        sql = 'INSERT INTO errors ("sourceaddress", "targetaddress", "tntxid", "ethtxid", "amount", "error", "exception") VALUES (%s, %s, %s, %s, %s, %s, %s)'
        values = (sourceAddress, targetAddress, tntxid, ethtxid, amount, error, exception)

        dbCon = self.openConn()
        cursor = dbCon.cursor()
        cursor.execute(sql, values)
        cursor.close()
        self.closeConn(dbCon)

    def getErrors(self):
        sql = 'SELECT * FROM errors'

        dbCon = self.openConn()
        cursor = dbCon.cursor()
        cursor.execute(sql)
        qryResult = cursor.fetchall()
        cursor.close()
        self.closeConn(dbCon)

        if len(qryResult) > 0:
            return qryResult
        else:
            return {}

    def getError(self, sourceAddress='', targetAddress=''):
        if sourceAddress != '':
            sql = 'SELECT error, tntxid, ethtxid FROM errors WHERE sourceaddress = %s ORDER BY id DESC LIMIT 1'
            values = (sourceAddress,)
        elif targetAddress != '':
            sql = 'SELECT error, tntxid, ethtxid FROM errors WHERE targetaddress = %s ORDER BY id DESC LIMIT 1'
            values = (targetAddress,)
        else:
            return {}

        dbCon = self.openConn()
        cursor = dbCon.cursor()
        cursor.execute(sql, values)
        qryResult = cursor.fetchall()
        cursor.close()
        self.closeConn(dbCon)

        if len(qryResult) > 0:
            return qryResult
        else:
            return {}

#verified table related
    def getVerifiedAll(self):
        sql = 'SELECT * FROM verified'

        dbCon = self.openConn()
        cursor = dbCon.cursor()
        cursor.execute(sql)
        qryResult = cursor.fetchall()
        cursor.close()
        self.closeConn(dbCon)

        if len(qryResult) > 0:
            return qryResult
        else:
            return {}

    def getUnVerified(self):
        sql = 'SELECT * FROM verified WHERE block = 0'

        dbCon = self.openConn()
        cursor = dbCon.cursor()
        cursor.execute(sql)
        qryResult = cursor.fetchall()
        cursor.close()
        self.closeConn(dbCon)

        if len(qryResult) > 0:
            return qryResult
        else:
            return {}

    def getVerified(self, tx):
        sql = 'SELECT block FROM verified WHERE tx = %s'
        values = (tx,)

        dbCon = self.openConn()
        cursor = dbCon.cursor()
        cursor.execute(sql, values)
        qryResult = cursor.fetchall()
        cursor.close()
        self.closeConn(dbCon)

        if len(qryResult) > 0:
            return qryResult[0][0]
        else:
            return None

    def insVerified(self, chain, tx, block):
        if self.getVerified(tx) is None:
            sql = 'INSERT INTO verified ("chain", "tx", "block") VALUES (%s, %s, %s)'
            values = (chain, tx, block)

            dbCon = self.openConn()
            cursor = dbCon.cursor()
            cursor.execute(sql, values)
            cursor.close()
            self.closeConn(dbCon)
        else:
            sql = 'UPDATE verified SET block = %s WHERE "tx" = %s'
            values = (block, tx)

            dbCon = self.openConn()
            cursor = dbCon.cursor()
            cursor.execute(sql, values)
            cursor.close()
            self.closeConn(dbCon)

#other
    def checkTXs(self, address):
        if address == '':
            dbCon = self.openConn()
            cursor = dbCon.cursor()
            sql = "SELECT e.sourceaddress, e.targetaddress, e.tntxid, e.ethtxid as OtherTxId, COALESCE(v.block, 0) as TNVerBlock, COALESCE(v2.block, 0) as OtherVerBlock, e.amount, CASE WHEN e.targetaddress LIKE '3J%%' THEN 'Deposit' ELSE 'Withdraw' END TypeTX, " \
            "CASE WHEN e.targetaddress LIKE '3J%%' AND v.block IS NOT NULL THEN 'verified' WHEN e.targetaddress NOT LIKE '3J%%' AND v2.block IS NOT NULL AND v2.block > 0 THEN 'verified' ELSE 'unverified' END Status " \
            "FROM executed e LEFT JOIN verified v ON e.tntxid = v.tx LEFT JOIN verified v2 ON e.ethtxid = v2.tx "
            cursor.execute(sql)
        else:
            dbCon = self.openConn()
            cursor = dbCon.cursor()
            sql = "SELECT e.sourceaddress, e.targetaddress, e.tntxid, e.ethtxid as OtherTxId, COALESCE(v.block, 0) as TNVerBlock, COALESCE(v2.block, 0) as OtherVerBlock, e.amount, CASE WHEN e.targetaddress LIKE '3J%%' THEN 'Deposit' ELSE 'Withdraw' END TypeTX, " \
            "CASE WHEN e.targetaddress LIKE '3J%%' AND v.block IS NOT NULL THEN 'verified' WHEN e.targetaddress NOT LIKE '3J%%' AND v2.block IS NOT NULL AND v2.block > 0 THEN 'verified' ELSE 'unverified' END Status " \
            "FROM executed e LEFT JOIN verified v ON e.tntxid = v.tx LEFT JOIN verified v2 ON e.ethtxid = v2.tx WHERE (e.sourceaddress = %s or e.targetaddress = %s)"
            values = (address, address)
            cursor.execute(sql, values)

        tx = [dict((cursor.description[i][0], value) for i, value in enumerate(row)) for row in cursor.fetchall()]
        cursor.close()
        self.closeConn(dbCon)

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

        dbCon = self.openConn()
        cursor = dbCon.cursor()
        cursor.execute(sql, values)
        qryResult = cursor.fetchall()
        cursor.close()
        self.closeConn(dbCon)

        if len(qryResult) == 0:
            Fees = 0
        else:
            Fees = qryResult[0][0]

        return { 'totalFees': Fees }