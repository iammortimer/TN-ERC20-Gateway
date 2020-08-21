import os
import requests
import traceback
import time
from dbClass import dbCalls
from otherClass import otherCalls

class etherscanCalls(object):
    def __init__(self, config):
        self.config = config
        self.db = dbCalls(config)
        self.otc = otherCalls(config)

        self.apikey = self.config['other']['etherscan-apikey']
        self.url = 'https://api.etherscan.io/api?'

        self.lastScannedBlock = self.db.lastScannedBlock("ETH")

    def currentBlock(self):
        time.sleep(2)
        url = self.url + 'module=proxy&action=eth_blockNumber&apikey=' + self.apikey
        result = requests.get(url).json()

        return int(result['result'], 16)

    def getBlock(self, height):
        time.sleep(2)
        url = self.url + 'module=account&action=tokentx&address=' + self.config['other']['gatewayAddress'] + '&startblock=' + str(height) + '&endblock=' + str((self.currentBlock() - self.config['other']['confirmations'])) + '&sort=asc&apikey=' + self.apikey
        result = requests.get(url).json()

        if result['status'] == '1':
            result = {'transactions': result['result']}
        else:
            result = {'transactions': []}

        return result

    def currentBalance(self):
        time.sleep(2)
        url = self.url + 'module=account&action=tokenbalance&contractaddress=' + self.config['other']['contract']['address'] + '&address=' + self.config['other']['gatewayAddress'] + '&tag=latest&apikey=' + self.apikey
        result = requests.get(url).json()

        if result['status'] == '1':
            balance = int(result['result'])
            balance /= pow(10, self.config['other']['contract']['decimals'])
        else:
            balance = 0

        return balance

    def normalizeAddress(self, address):
        return self.otc.normalizeAddress(address)

    def validateAddress(self, address):
        return self.otc.validateAddress(address)

    def verifyTx(self, txId, sourceAddress = '', targetAddress = ''):
        time.sleep(2)
        if type(txId) == str:
            txid = txId
        else: 
            txid = txId.hex()

        url = self.url + 'module=proxy&action=eth_getTransactionReceipt&txhash=' + txid + '&apikey=' + self.apikey
        try:
            verified = requests.get(url).json()['result']

            if int(verified['status'], 16) == 1:
                self.db.insVerified("ETH", txid, int(verified['blockNumber'], 16))
                print('INFO: tx to eth verified!')

                self.db.delTunnel(sourceAddress, targetAddress)
            elif int(verified['status'], 16) == 0:
                print('ERROR: tx failed to send!')
                self.resendTx(txId)
        except:
            self.db.insVerified("ETH", txid, 0)
            print('WARN: tx to eth not verified!')

    def checkTx(self, tx):
        #check the transaction
        result = None

        tx['contractAddress'] = self.normalizeAddress(tx['contractAddress'])
        tx['to'] = self.normalizeAddress(tx['to'])

        if tx['contractAddress'] == self.config['other']['contract']['address'] and tx['to'] == self.config['other']['gatewayAddress']:
                sender = self.normalizeAddress(tx['from'])
                amount = int(tx['value']) / 10 ** self.config['other']['contract']['decimals']

                if not self.db.didWeSendTx(tx['hash']): 
                    result = { 'sender': sender, 'function': 'transfer', 'recipient': tx['to'], 'amount': amount, 'token': self.config['other']['contract']['address'], 'id': tx['hash'] }

        return result

    def sendTx(self, targetAddress, amount, gasprice = None, gas = None):
        return self.otc.sendTx(targetAddress, amount, gasprice, gas)

    def resendTx(self, txId):
        self.otc.resendTx(txId)
