import os
import sqlite3 as sqlite
import time
import PyCWaves
import traceback
import sharedfunc
from web3 import Web3
from ethtoken.abi import EIP20_ABI

class ETHChecker(object):
    def __init__(self, config):
        self.config = config
        self.dbCon = sqlite.connect('gateway.db')
        self.w3 = self.getWeb3Instance()

        self.pwTN = PyCWaves.PyCWaves()
        self.pwTN.setNode(node=self.config['tn']['node'], chain=self.config['tn']['network'], chain_id='L')
        seed = os.getenv(self.config['tn']['seedenvname'], self.config['tn']['gatewaySeed'])
        self.tnAddress = self.pwTN.Address(seed=seed)
        self.tnAsset = self.pwTN.Asset(self.config['tn']['assetId'])

        cursor = self.dbCon.cursor()
        self.lastScannedBlock = cursor.execute('SELECT height FROM heights WHERE chain = "ETH"').fetchall()[0][0]

    def getWeb3Instance(self):
        instance = None

        if self.config['erc20']['node'].startswith('http'):
            instance = Web3(Web3.HTTPProvider(self.config['erc20']['node']))
        else:
            instance = Web3()

        return instance

    def getCurrentBlock(self):
        latestBlock = self.w3.eth.blockNumber

        return latestBlock

    def run(self):
        #main routine to run continuesly
        print('started checking tn blocks at: ' + str(self.lastScannedBlock))

        self.dbCon = sqlite.connect('gateway.db')
        while True:
            try:
                nextblock = self.getCurrentBlock() - self.config['erc20']['confirmations']

                if nextblock > self.lastScannedBlock:
                    self.lastScannedBlock += 1
                    self.checkBlock(self.lastScannedBlock)
                    cursor = self.dbCon.cursor()
                    cursor.execute('UPDATE heights SET "height" = ' + str(self.lastScannedBlock) + ' WHERE "chain" = "ETH"')
                    self.dbCon.commit()
            except Exception as e:
                self.lastScannedBlock -= 1
                print('Something went wrong during ETH block iteration: ')
                print(traceback.TracebackException.from_exception(e))

            time.sleep(self.config['erc20']['timeInBetweenChecks'])

    def checkBlock(self, heightToCheck):
        #check content of the block for valid transactions
        block = self.w3.eth.getBlock(heightToCheck)
        for transaction in block['transactions']:
            txInfo = self.checkTx(transaction)

            if txInfo is not None:
                cursor = self.dbCon.cursor()
                res = cursor.execute('SELECT targetAddress FROM tunnel WHERE sourceAddress ="' + txInfo['sender'] + '"').fetchall()
                if len(res) == 0:
                    self.faultHandler(txInfo, 'notunnel')
                else:
                    targetAddress = res[0][0]
                    amount = txInfo['amount']
                    amount -= self.config['tn']['fee']
                    amount *= pow(10, self.config['tn']['decimals'])
                    amount = int(round(amount))

                    try:
                        addr = self.pwTN.Address(targetAddress)
                        if self.config['tn']['assetId'] == 'TN':
                            tx = self.tnAddress.sendWaves(addr, amount, 'Thanks for using our service!', txFee=2000000)
                        else:
                            tx = self.tnAddress.sendAsset(addr, self.tnAsset, amount, 'Thanks for using our service!', txFee=2000000)

                        if 'error' in tx:
                            self.faultHandler(txInfo, "senderror", e=tx['message'])
                        else:
                            print("send tx: " + str(tx))

                            cursor = self.dbCon.cursor()
                            amount /= pow(10, self.config['tn']['decimals'])
                            cursor.execute('INSERT INTO executed ("sourceAddress", "targetAddress", "ethTxId", "tnTxId", "amount", "amountFee") VALUES ("' + txInfo['sender'] + '", "' + targetAddress + '", "' + transaction.hex() + '", "' + tx['id'] + '", "' + str(round(amount)) + '", "' + str(self.config['tn']['fee']) + '")')
                            self.dbCon.commit()
                            print('send tokens from waves to tn!')

                            cursor = self.dbCon.cursor()
                            cursor.execute('DELETE FROM tunnel WHERE sourceAddress = "' + txInfo['sender'] + '" and targetAddress = "' + targetAddress + '"')
                            self.dbCon.commit()
                            
                    except Exception as e:
                        self.faultHandler(txInfo, "txerror", e=e)

    def checkTx(self, tx):
        #check the transaction
        result = None
        transaction = self.w3.eth.getTransaction(tx)

        if transaction['to'] == self.config['erc20']['contract']['address'] and transaction['input'].startswith('0xa9059cbb'):
            transactionreceipt = self.w3.eth.getTransactionReceipt(tx)
            if transactionreceipt['status']:
                contract = self.w3.eth.contract(address=self.config['erc20']['contract']['address'], abi=EIP20_ABI)
                sender = transaction['from']
                decodedInput = contract.decode_function_input(transaction['input'])
                recipient = decodedInput[1]['_to']
                if recipient == self.config['erc20']['gatewayAddress']:
                    amount = decodedInput[1]['_value'] / 10 ** self.config['erc20']['contract']['decimals']

                    cursor = self.dbCon.cursor()
                    res = cursor.execute('SELECT tnTxId FROM executed WHERE ethTxId = "' + tx.hex() + '"').fetchall()
                    if len(res) == 0: result =  { 'sender': sender, 'function': 'transfer', 'recipient': recipient, 'amount': amount, 'token': self.config['erc20']['contract']['address'], 'id': tx.hex() }

        return result
        
    def faultHandler(self, tx, error, e=""):
        #handle transfers to the gateway that have problems
        amount = tx['amount']
        timestampStr = sharedfunc.getnow()

        if error == "notunnel":
            cursor = self.dbCon.cursor()
            cursor.execute('INSERT INTO errors ("sourceAddress", "targetAddress", "tnTxId", "ethTxId", "amount", "error") VALUES ("' + tx['sender'] + '", "", "", "' + tx['id'] + '", "' + str(amount) + '", "no tunnel found for sender")')
            self.dbCon.commit()
            print(timestampStr + " - Error: no tunnel found for transaction from " + tx['sender'] + " - check errors table.")

        if error == "txerror":
            targetAddress = tx['recipient']
            cursor = self.dbCon.cursor()
            cursor.execute('INSERT INTO errors ("sourceAddress", "targetAddress", "tnTxId", "ethTxId", "amount", "error", "exception") VALUES ("' + tx['sender'] + '", "' + targetAddress + '", "", "' + tx['id'] + '", "' + str(amount) + '", "tx error, possible incorrect address", "' + str(e) + '")')
            self.dbCon.commit()
            print(timestampStr + " - Error: on outgoing transaction for transaction from " + tx['sender'] + " - check errors table.")

        if error == "senderror":
            targetAddress = tx['recipient']
            cursor = self.dbCon.cursor()
            cursor.execute('INSERT INTO errors ("sourceAddress", "targetAddress", "tnTxId", "ethTxId", "amount", "error", "exception") VALUES ("' + tx['sender'] + '", "' + targetAddress + '", "", "' + tx['id'] + '", "' + str(amount) + '", "tx error, check exception error", "' + str(e) + '")')
            self.dbCon.commit()
            print(timestampStr + " - Error: on outgoing transaction for transaction from " + tx['sender'] + " - check errors table.")
