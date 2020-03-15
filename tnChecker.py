import os
import sqlite3 as sqlite
import requests
import time
import base58
import PyCWaves
import traceback
import sharedfunc
from web3 import Web3
from ethtoken.abi import EIP20_ABI
from verification import verifier

class TNChecker(object):
    def __init__(self, config):
        self.config = config
        self.dbCon = sqlite.connect('gateway.db')

        self.node = self.config['tn']['node']
        self.w3 = Web3(Web3.HTTPProvider(self.config['erc20']['node']))
        self.privatekey = os.getenv(self.config['erc20']['seedenvname'], self.config['erc20']['privateKey'])
        self.verifier = verifier(config)

        cursor = self.dbCon.cursor()
        self.lastScannedBlock = cursor.execute('SELECT height FROM heights WHERE chain = "TN"').fetchall()[0][0]

    def getCurrentBlock(self):
        #return current block on the chain - try/except in case of timeouts
        try:
            CurrentBlock = requests.get(self.node + '/blocks/height').json()['height'] - 1
        except:
            CurrentBlock = 0

        return CurrentBlock

    def run(self):
        #main routine to run continuesly
        print('started checking tn blocks at: ' + str(self.lastScannedBlock))

        self.dbCon = sqlite.connect('gateway.db')
        while True:
            try:
                nextblock = self.getCurrentBlock() - self.config['tn']['confirmations']

                if nextblock > self.lastScannedBlock:
                    self.lastScannedBlock += 1
                    self.checkBlock(self.lastScannedBlock)
                    cursor = self.dbCon.cursor()
                    cursor.execute('UPDATE heights SET "height" = ' + str(self.lastScannedBlock) + ' WHERE "chain" = "TN"')
                    self.dbCon.commit()
            except Exception as e:
                self.lastScannedBlock -= 1
                print('Something went wrong during tn block iteration: ')
                print(traceback.TracebackException.from_exception(e))

            time.sleep(self.config['tn']['timeInBetweenChecks'])

    def checkBlock(self, heightToCheck):
        #check content of the block for valid transactions
        block =  requests.get(self.node + '/blocks/at/' + str(heightToCheck)).json()
        for transaction in block['transactions']:
            if self.checkTx(transaction):
                targetAddress = base58.b58decode(transaction['attachment']).decode()
                targetAddress = self.w3.toChecksumAddress(targetAddress)

                if not(self.w3.isAddress(targetAddress)):
                    self.faultHandler(transaction, "txerror")
                else:
                    amount = transaction['amount'] / pow(10, self.config['tn']['decimals'])
                    amount -= self.config['erc20']['fee']
                    amount *= pow(10, self.config['erc20']['contract']['decimals'])
                    amount = int(round(amount))

                    try:
                        token = self.w3.eth.contract(address=self.config['erc20']['contract']['address'], abi=EIP20_ABI)
                        nonce = self.w3.eth.getTransactionCount(self.config['erc20']['gatewayAddress'])
                        if self.config['erc20']['gasprice'] > 0:
                            gasprice = self.w3.toWei(self.config['erc20']['gasprice'], 'gwei')
                        else:
                            gasprice = int(self.w3.eth.gasPrice * 1.1)

                        tx = token.functions.transfer(targetAddress, amount).buildTransaction({
                            'chainId': 1,
                            'gas': self.config['erc20']['gas'],
                            'gasPrice': gasprice,
                            'nonce': nonce
                        })
                        signed_tx = self.w3.eth.account.signTransaction(tx, private_key=self.privatekey)
                        txId = self.w3.eth.sendRawTransaction(signed_tx.rawTransaction)

                        if not(str(txId.hex()).startswith('0x')):
                            self.faultHandler(transaction, "senderror", e=txId.hex())
                        else:
                            print("send tx: " + str(txId.hex()))

                            cursor = self.dbCon.cursor()
                            amount /= pow(10, self.config['erc20']['contract']['decimals'])
                            cursor.execute('INSERT INTO executed ("sourceAddress", "targetAddress", "tnTxId", "ethTxId", "amount", "amountFee") VALUES ("' + transaction['sender'] + '", "' + targetAddress + '", "' + transaction['id'] + '", "' + txId.hex() + '", "' + str(round(amount)) + '", "' + str(self.config['erc20']['fee']) + '")')
                            self.dbCon.commit()
                            print('send tokens from tn to erc20!')
                    except Exception as e:
                        self.faultHandler(transaction, "txerror", e=e)

                    self.verifier.verifyOther(txId)

    def checkTx(self, tx):
        #check the transaction
        if tx['type'] == 4 and tx['recipient'] == self.config['tn']['gatewayAddress'] and tx['assetId'] == self.config['tn']['assetId']:
            #check if there is an attachment
            targetAddress = base58.b58decode(tx['attachment']).decode()
            if len(targetAddress) > 1:
                #check if we already processed this tx
                cursor = self.dbCon.cursor()
                result = cursor.execute('SELECT ethTxId FROM executed WHERE tnTxId = "' + tx['id'] + '"').fetchall()

                if len(result) == 0: return True
            else:
                self.faultHandler(tx, 'noattachment')

        return False
        
    def faultHandler(self, tx, error, e=""):
        #handle transfers to the gateway that have problems
        amount = tx['amount'] / pow(10, self.config['tn']['decimals'])
        timestampStr = sharedfunc.getnow()

        if error == "noattachment":
            cursor = self.dbCon.cursor()
            cursor.execute('INSERT INTO errors ("sourceAddress", "targetAddress", "ethTxId", "tnTxId", "amount", "error") VALUES ("' + tx['sender'] + '", "", "", "' + tx['id'] + '", "' + str(amount) + '", "no attachment found on transaction")')
            self.dbCon.commit()
            print(timestampStr + " - Error: no attachment found on transaction from " + tx['sender'] + " - check errors table.")

        if error == "txerror":
            targetAddress = base58.b58decode(tx['attachment']).decode()
            cursor = self.dbCon.cursor()
            cursor.execute('INSERT INTO errors ("sourceAddress", "targetAddress", "ethTxId", "tnTxId", "amount", "error", "exception") VALUES ("' + tx['sender'] + '", "' + targetAddress + '", "", "' + tx['id'] + '", "' + str(amount) + '", "tx error, possible incorrect address", "' + str(e) + '")')
            self.dbCon.commit()
            print(timestampStr + " - Error: on outgoing transaction for transaction from " + tx['sender'] + " - check errors table.")

        if error == "senderror":
            targetAddress = base58.b58decode(tx['attachment']).decode()
            cursor = self.dbCon.cursor()
            cursor.execute('INSERT INTO errors ("sourceAddress", "targetAddress", "ethTxId", "tnTxId", "amount", "error", "exception") VALUES ("' + tx['sender'] + '", "' + targetAddress + '", "", "' + tx['id'] + '", "' + str(amount) + '", "tx error, check exception error", "' + str(e) + '")')
            self.dbCon.commit()
            print(timestampStr + " - Error: on outgoing transaction for transaction from " + tx['sender'] + " - check errors table.")
