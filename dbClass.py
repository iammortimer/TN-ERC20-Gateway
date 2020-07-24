import PyCWaves
import sqlite3 as sqlite
from datetime import timedelta
import datetime

class dbCalls(object):
    def __init__(self, config):
        self.config = config
        self.dbCon = sqlite.connect('gateway.db', check_same_thread=False)
        self.pwTN = PyCWaves.PyCWaves()
        self.pwTN.THROW_EXCEPTION_ON_ERROR = True
        self.pwTN.setNode(node=self.config['tn']['node'], chain=self.config['tn']['network'], chain_id='L')

#heights table related
    def lastScannedBlock(self, chain):
        sql = 'SELECT height FROM heights WHERE chain = ?'
        values = (chain,)

        cursor = self.dbCon.cursor()
        qryResult = cursor.execute(sql, values).fetchall()

        if len(qryResult) > 0:
            return qryResult[0][0]
        else:
            return {}

    def getHeights(self):
        sql = 'SELECT chain, height FROM heights'

        cursor = self.dbCon.cursor()
        qryResult = cursor.execute(sql).fetchall()

        if len(qryResult) > 0:
            return qryResult
        else:
            return {}

    def updHeights(self, block, chain):
        sql = 'UPDATE heights SET "height" = ? WHERE chain = ?'
        values = (block, chain)

        cursor = self.dbCon.cursor()
        qryResult = cursor.execute(sql, values)
        self.dbCon.commit()

#tunnel table related
    def doWeHaveTunnels(self):
        sql = 'SELECT * FROM tunnel WHERE status = "created"'

        cursor = self.dbCon.cursor()
        qryResult = cursor.execute(sql).fetchall()

        if len(qryResult) > 0:
            return True
        else:
            return False

    def getTargetAddress(self, sourceAddress):
        sql = 'SELECT targetAddress FROM tunnel WHERE status <> "error" AND sourceAddress = ?'
        values = (sourceAddress,)

        cursor = self.dbCon.cursor()
        qryResult = cursor.execute(sql, values).fetchall()

        if len(qryResult) > 0:
            return qryResult[0][0]
        else:
            return {}

    def getSourceAddress(self, targetAddress):
        sql = 'SELECT sourceAddress FROM tunnel WHERE status <> "error" AND targetAddress = ?'
        values = (targetAddress,)

        cursor = self.dbCon.cursor()
        qryResult = cursor.execute(sql, values).fetchall()

        if len(qryResult) > 0:
            return qryResult[0][0]
        else:
            return {}

    def getTunnelStatus(self, targetAddress = '', sourceAddress = ''):
        if targetAddress != '':
            sql = 'SELECT status FROM tunnel WHERE targetAddress = ? ORDER BY id DESC LIMIT 1'
            values = (targetAddress,)
        elif  sourceAddress != '':
            sql = 'SELECT status FROM tunnel WHERE sourceAddress = ? ORDER BY id DESC LIMIT 1'
            values = (sourceAddress,)
        else:
            return {}

        cursor = self.dbCon.cursor()
        qryResult = cursor.execute(sql, values).fetchall()

        if len(qryResult) > 0:
            return qryResult
        else:
            return {}

    def getTunnels(self, status = ''):
        if status != '':
            sql = 'SELECT sourceAddress, targetAddress FROM tunnel WHERE status = ?'
            values = (status,)
        else:
            return {}

        cursor = self.dbCon.cursor()
        qryResult = cursor.execute(sql, values).fetchall()

        if len(qryResult) > 0:
            return qryResult
        else:
            return {}

    def insTunnel(self, status, sourceAddress, targetAddress):
        sql = 'INSERT INTO tunnel ("sourceAddress", "targetAddress", "status", "timestamp") VALUES (?, ?, ?, CURRENT_TIMESTAMP)'
        values = (sourceAddress, targetAddress, status)

        cursor = self.dbCon.cursor()
        qryResult = cursor.execute(sql, values)
        self.dbCon.commit()

    def updTunnel(self, status, sourceAddress, targetAddress, statusOld = ''):
        if statusOld == '':
            statusOld = 'created'

        sql = 'UPDATE tunnel SET "status" = ?, "timestamp" = CURRENT_TIMESTAMP WHERE status = ? AND sourceAddress = ? and targetAddress = ?'
        values = (status, statusOld, sourceAddress, targetAddress)

        cursor = self.dbCon.cursor()
        qryResult = cursor.execute(sql, values)
        self.dbCon.commit()

    def delTunnel(self, sourceAddress, targetAddress):
        sql = 'DELETE FROM tunnel WHERE sourceAddress = ? and targetAddress = ?'
        values = (sourceAddress, targetAddress)

        cursor = self.dbCon.cursor()
        qryResult = cursor.execute(sql, values)
        self.dbCon.commit()

#executed table related
    def insExecuted(self, sourceAddress, targetAddress, ethTxID, tnTxID, amount, amountFee):
        sql = 'INSERT INTO executed ("sourceAddress", "targetAddress", "ethTxId", "tnTxId", "amount", "amountFee") VALUES (?, ?, ?, ?, ?, ?)'
        values = (sourceAddress, targetAddress, ethTxID, tnTxID, amount, amountFee)

        cursor = self.dbCon.cursor()
        qryResult = cursor.execute(sql, values)
        self.dbCon.commit()

    def updExecuted(self, id, sourceAddress, targetAddress, ethTxID, tnTxID, amount, amountFee):
        sql = 'UPDATE executed SET "sourceAddress" = ?, "targetAddress" = ?, "ethTxId" = ?, "tnTxId" = ?, "amount" = ?, "amountFee" = ?) WHERE id = ?'
        values = (sourceAddress, targetAddress, ethTxID, tnTxID, amount, amountFee, id)

        cursor = self.dbCon.cursor()
        qryResult = cursor.execute(sql, values)
        self.dbCon.commit()

    def didWeSendTx(self, txid):
        sql = 'SELECT * FROM executed WHERE (ethTxId = ? OR tnTxId = ?)'
        values = (txid, txid)

        cursor = self.dbCon.cursor()
        qryResult = cursor.execute(sql, values).fetchall()

        if len(qryResult) > 0:
            return True
        else:
            return False

    def getExecutedAll(self):
        sql = 'SELECT * FROM executed'

        cursor = self.dbCon.cursor()
        qryResult = cursor.execute(sql).fetchall()

        if len(qryResult) > 0:
            return qryResult
        else:
            return {}

    def getExecuted(self, sourceAddress = '', targetAddress = '', ethTxId = '', tnTxId = ''):
        if sourceAddress != '':
            sql = 'SELECT ethTxId FROM executed WHERE sourceAddress = ? ORDER BY id DESC LIMIT 1'
            values = (sourceAddress,)
        elif targetAddress != '':
            sql = 'SELECT tnTxId FROM executed WHERE targetAddress = ? ORDER BY id DESC LIMIT 1'
            values = (targetAddress,)
        elif ethTxId != '':
            sql = 'SELECT * FROM executed WHERE ethTxId = ? ORDER BY id DESC LIMIT 1'
            values = (ethTxId,)
        elif tnTxId != '':
            sql = 'SELECT * FROM executed WHERE tnTxId = ? ORDER BY id DESC LIMIT 1'
            values = (tnTxId,)
        else:
            return {}

        cursor = self.dbCon.cursor()
        qryResult = cursor.execute(sql, values).fetchall()

        if len(qryResult) > 0:
            return qryResult
        else:
            return {}

#error table related
    def insError(self, sourceAddress, targetAddress, tnTxId, ethTxId, amount, error, exception = ''):
        sql = 'INSERT INTO errors ("sourceAddress", "targetAddress", "tnTxId", "ethTxId", "amount", "error", "exception") VALUES (?, ?, ?, ?, ?, ?, ?)'
        values = (sourceAddress, targetAddress, tnTxId, ethTxId, amount, error, exception)

        cursor = self.dbCon.cursor()
        qryResult = cursor.execute(sql, values)
        self.dbCon.commit()

    def getErrors(self):
        sql = 'SELECT * FROM errors'

        cursor = self.dbCon.cursor()
        qryResult = cursor.execute(sql).fetchall()

        if len(qryResult) > 0:
            return qryResult
        else:
            return {}

    def getError(self, sourceAddress='', targetAddress=''):
        if sourceAddress != '':
            sql = 'SELECT error, tntxid, ethtxid FROM errors WHERE sourceAddress = ? ORDER BY id DESC LIMIT 1'
            values = (sourceAddress,)
        elif targetAddress != '':
            sql = 'SELECT error, tntxid, ethtxid FROM errors WHERE targetAddress = ? ORDER BY id DESC LIMIT 1'
            values = (targetAddress,)
        else:
            return {}

        cursor = self.dbCon.cursor()
        qryResult = cursor.execute(sql, values).fetchall()

        if len(qryResult) > 0:
            return qryResult
        else:
            return {}

#verified table related
    def getVerifiedAll(self):
        sql = 'SELECT * FROM verified'

        cursor = self.dbCon.cursor()
        qryResult = cursor.execute(sql).fetchall()

        if len(qryResult) > 0:
            return qryResult
        else:
            return {}

    def getVerified(self, tx):
        sql = 'SELECT block FROM verified WHERE tx = ?'
        values = (tx,)

        cursor = self.dbCon.cursor()
        qryResult = cursor.execute(sql, values).fetchall()

        if len(qryResult) > 0:
            return qryResult[0][0]
        else:
            return None

    def insVerified(self, chain, tx, block):
        if self.getVerified(tx) is None:
            sql = 'INSERT INTO verified ("chain", "tx", "block") VALUES (?, ?, ?)'
            values = (chain, tx, block)

            cursor = self.dbCon.cursor()
            qryResult = cursor.execute(sql, values)
            self.dbCon.commit()

#other
    def checkTXs(self, address):
        if len(address) == 0:
            cursor = self.dbCon.cursor()
            sql = "SELECT e.sourceAddress, e.targetAddress, e.tnTxId, e.ethTxId as 'OtherTxId', ifnull(v.block, 0) as 'TNVerBlock', ifnull(v2.block, 0) as 'OtherVerBlock', e.amount, CASE WHEN e.targetAddress LIKE '3J%' THEN 'Deposit' ELSE 'Withdraw' END 'TypeTX', " \
            "CASE WHEN e.targetAddress LIKE '3J%' AND v.block IS NOT NULL THEN 'verified' WHEN e.targetAddress NOT LIKE '3J%' AND v2.block IS NOT NULL AND v2.block IS NOT 0 THEN 'verified' ELSE 'unverified' END 'Status' " \
            "FROM executed e LEFT JOIN verified v ON e.tnTxId = v.tx LEFT JOIN verified v2 ON e.ethTxId = v2.tx "
            cursor.execute(sql)
        else:
            if not self.pwTN.validateAddress(address):
                return {'error': 'invalid address'}
            else:
                cursor = self.dbCon.cursor()
                sql = "SELECT e.sourceAddress, e.targetAddress, e.tnTxId, e.ethTxId as 'OtherTxId', ifnull(v.block, 0) as 'TNVerBlock', ifnull(v2.block, 0) as 'OtherVerBlock', e.amount, CASE WHEN e.targetAddress LIKE '3J%' THEN 'Deposit' ELSE 'Withdraw' END 'TypeTX', " \
                "CASE WHEN e.targetAddress LIKE '3J%' AND v.block IS NOT NULL THEN 'verified' WHEN e.targetAddress NOT LIKE '3J%' AND v2.block IS NOT NULL AND v2.block IS NOT 0 THEN 'verified' ELSE 'unverified' END 'Status' " \
                "FROM executed e LEFT JOIN verified v ON e.tnTxId = v.tx LEFT JOIN verified v2 ON e.ethTxId = v2.tx WHERE (e.sourceAddress = ? or e.targetAddress = ?)"
                cursor.execute(sql, (address, address))

        tx = [dict((cursor.description[i][0], value) for i, value in enumerate(row)) for row in cursor.fetchall()]
        cursor.connection.close()

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

        result = self.dbCon.cursor().execute("SELECT SUM(amountFee) as totalFee from executed WHERE timestamp > ? and timestamp < ?", values).fetchall()
        if len(result) == 0:
            Fees = 0
        else:
            Fees = result[0][0]

        return { 'totalFees': Fees }