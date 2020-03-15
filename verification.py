import sqlite3 as sqlite
import time
import PyCWaves
from web3 import Web3

class verifier(object):
    def __init__(self, config):
        self.config = config
        self.dbCon = sqlite.connect('gateway.db')

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
