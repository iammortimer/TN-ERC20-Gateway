import sqlite3 as sqlite
import time
import PyCWaves
from web3 import Web3

class verifier(object):
    def __init__(self, config):
        self.config = config
        self.dbCon = sqlite.connect('gateway.db', check_same_thread=False)

        self.w3 = Web3(Web3.HTTPProvider(self.config['erc20']['node']))

        self.pwTN = PyCWaves.PyCWaves()
        self.pwTN.setNode(node=self.config['tn']['node'], chain=self.config['tn']['network'], chain_id='L')

    def verifyOther(self, txId):
        try:
            verified = self.w3.eth.waitForTransactionReceipt(txId.hex(), timeout=120)

            if verified['blockNumber'] > 0:
                values = ("ETH", txId.hex(), verified['blockNumber'])
                cursor = self.dbCon.cursor()
                cursor.execute('INSERT INTO verified ("chain", "tx", "block") VALUES (?, ?, ?)', values)
                self.dbCon.commit()
                print('tx to eth verified!')
            else:
                values = ("ETH", txId.hex(), 0)
                cursor = self.dbCon.cursor()
                cursor.execute('INSERT INTO verified ("chain", "tx", "block") VALUES (?, ?, ?)', values)
                self.dbCon.commit()
                print('tx to eth not verified!')
        except:
            values = ("ETH", txId.hex(), 0)
            cursor = self.dbCon.cursor()
            cursor.execute('INSERT INTO verified ("chain", "tx", "block") VALUES (?, ?, ?)', values)
            self.dbCon.commit()
            print('tx to eth not verified!')

    def verifyTN(self, tx):
        try:
            time.sleep(60)
            verified = self.pwTN.tx(tx['id'])

            if verified['height'] > 0:
                values = ("TN", tx['id'], verified['height'])
                cursor = self.dbCon.cursor()
                cursor.execute('INSERT INTO verified ("chain", "tx", "block") VALUES (?, ?, ?)', values)
                self.dbCon.commit()
                print('tx to tn verified!')
            else:
                values = ("TN", tx['id'], 0)
                cursor = self.dbCon.cursor()
                cursor.execute('INSERT INTO verified ("chain", "tx", "block") VALUES (?, ?, ?)', values)
                self.dbCon.commit()
                print('tx to tn not verified!')
        except:
            values = ("TN", tx['id'], 0)
            cursor = self.dbCon.cursor()
            cursor.execute('INSERT INTO verified ("chain", "tx", "block") VALUES (?, ?, ?)', values)
            self.dbCon.commit()
            print('tx to tn not verified!')

    def checkDeposit(self, address):
        if not self.pwTN.validateAddress(address):
            return {'error': 'invalid address'}
        else:
            cursor = self.dbCon.cursor()
            sql = 'SELECT tnTxId FROM executed WHERE targetAddress = ? ORDER BY id DESC LIMIT 1'
            tx = cursor.execute(sql, (address, )).fetchall()

            if len(tx) == 0:
                return {'error': 'no tx found'}
            else:
                sql = 'SELECT block FROM verified WHERE tx = ?'
                result = cursor.execute(sql, (tx[0][0], )).fetchall()

                if len(result) == 0:
                    return {'txVerified': False, 'tx': tx[0][0], 'block': 0} 
                else:
                    if result[0][0] > 0:
                        return {'txVerified': True, 'tx': tx[0][0], 'block': result[0][0]} 
                    else:
                        return {'txVerified': False, 'tx': tx[0][0], 'block': result[0][0]} 

    def checkWD(self, address):
        if not self.pwTN.validateAddress(address):
            return {'error': 'invalid address'}
        else:
            cursor = self.dbCon.cursor()
            sql = 'SELECT ethTxId FROM executed WHERE sourceAddress = ? ORDER BY id DESC LIMIT 1'
            tx = cursor.execute(sql, (address, )).fetchall()

            if len(tx) == 0:
                return {'error': 'no tx found'}
            else:
                sql = 'SELECT block FROM verified WHERE tx = ?'
                result = cursor.execute(sql, (tx[0][0], )).fetchall()

                if len(result) == 0:
                    return {'txVerified': False, 'tx': tx[0][0], 'block': 0} 
                else:
                    if result[0][0] > 0:
                        return {'txVerified': True, 'tx': tx[0][0], 'block': result[0][0]} 
                    else:
                        return {'txVerified': False, 'tx': tx[0][0], 'block': result[0][0]} 

    def checkTXs(self, address):
        if len(address) == 0:
            cursor = self.dbCon.cursor()
            sql = "SELECT e.sourceAddress, e.targetAddress, e.tnTxId, e.ethTxId as 'OtherTxId', v.block as 'TNVerBlock', v2.block as 'OtherVerBlock', e.amount, CASE WHEN e.targetAddress LIKE '3J%' THEN 'Deposit' ELSE 'Withdraw' END 'TypeTX', " \
            "CASE WHEN e.targetAddress LIKE '3J%' AND v.block IS NOT NULL THEN 'verified' WHEN e.targetAddress NOT LIKE '3J%' AND v2.block IS NOT NULL AND v2.block IS NOT 0 THEN 'verified' ELSE 'unverified' END 'Status' " \
            "FROM executed e LEFT JOIN verified v ON e.tnTxId = v.tx LEFT JOIN verified v2 ON e.ethTxId = v2.tx "
            cursor.execute(sql)

            tx = [dict((cursor.description[i][0], value) for i, value in enumerate(row)) for row in cursor.fetchall()]
            cursor.connection.close()

            if len(tx) == 0:
                return {'error': 'no tx found'}
            else:
                return tx
        else:
            if not self.pwTN.validateAddress(address):
                return {'error': 'invalid address'}
            else:
                cursor = self.dbCon.cursor()
                sql = "SELECT e.sourceAddress, e.targetAddress, e.tnTxId, e.ethTxId as 'OtherTxId', v.block as 'TNVerBlock', v2.block as 'OtherVerBlock', e.amount, CASE WHEN e.targetAddress LIKE '3J%' THEN 'Deposit' ELSE 'Withdraw' END 'TypeTX', " \
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
        from datetime import timedelta
        import datetime

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
        
        dbCon = sqlite.connect('gateway.db')
        values = (fromdate, todate)

        result = dbCon.cursor().execute("SELECT SUM(amountFee) as totalFee from executed WHERE timestamp > ? and timestamp < ?", values).fetchall()
        if len(result) == 0:
            Fees = 0
        else:
            Fees = result[0][0]

        return { 'totalFees': Fees }