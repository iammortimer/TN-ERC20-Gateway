from web3 import Web3
import sqlite3 as sqlite
import time
import datetime
import pywaves as pw
import traceback
from ethtoken.abi import EIP20_ABI

class ERC20Tunnel(object):

    def __init__(self, config):
        self.config = config
        self.dbCon = sqlite.connect('gateway.db')
        self.w3 = self.getWeb3Instance()

        cursor = self.dbCon.cursor()
        self.lastScannedBlock = cursor.execute('SELECT height FROM heights WHERE chain = "ETH"').fetchall()[0][0]

    def getWeb3Instance(self):
        instance = None

        if self.config['erc20']['endpoint'].startswith('http'):
            instance = Web3(Web3.HTTPProvider(self.config['erc20']['endpoint']))
        else:
            instance = Web3()

        return instance

    def getLatestBlockHeight(self):
        latestBlock = self.w3.eth.blockNumber

        return latestBlock

    def getTransaction(self, id):
        result = None
        #w3 = self.getWeb3Instance()
        transaction = self.w3.eth.getTransaction(id)

        if transaction['to'] == self.config['erc20']['contract']['address'] and transaction['input'].startswith('0xa9059cbb'):
            transactionreceipt = self.w3.eth.getTransactionReceipt(id)
            if transactionreceipt['status']:
                contract = self.w3.eth.contract(address=self.config['erc20']['contract']['address'], abi=EIP20_ABI)
                sender = transaction['from']
                decodedInput = contract.decode_function_input(transaction['input'])
                recipient = decodedInput[1]['_to']
                amount = decodedInput[1]['_value'] / 10 ** self.config['erc20']['contract']['decimals']
                result =  { 'sender': sender, 'function': 'transfer', 'recipient': recipient, 'amount': amount, 'token': self.config['erc20']['contract']['address'] }

        return result

    def iterate(self):
        dbCon = sqlite.connect('gateway.db')

        while True:
            try:
                nextBlockToCheck = self.getLatestBlockHeight() - self.config['erc20']['confirmations']

                if nextBlockToCheck > self.lastScannedBlock:
                    self.lastScannedBlock += 1
                    self.checkBlock(self.lastScannedBlock, dbCon)
                    cursor = dbCon.cursor()
                    cursor.execute('UPDATE heights SET "height" = ' + str(self.lastScannedBlock) + ' WHERE "chain" = "ETH"')
                    dbCon.commit()
            except Exception as e:
                print('Something went wrong during ETH block iteration: ')
                print(traceback.TracebackException.from_exception(e))

            time.sleep(self.config['erc20']['timeInBetweenChecks'])

    def checkBlock(self, heightToCheck, dbCon):
        print('checking eth block at: ' + str(heightToCheck))
        blockToCheck = self.w3.eth.getBlock(heightToCheck)
        for transaction in blockToCheck['transactions']:
            transactionInfo = self.getTransaction(transaction)

            if self.checkIfTransacitonValid(transactionInfo):
                cursor = dbCon.cursor()
                cursor.execute('SELECT targetAddress FROM tunnel WHERE sourceAddress ="' + transactionInfo['sender'] + '"')
                try:
                    targetAddress = cursor.fetchall()[0][0]
                except Exception as e:
                    targetAddress = 'no_tunnel_found'

                pw.setNode(node=self.config['tn']['node'], chain=self.config['tn']['network'], chain_id='L')
                tnAddress = pw.Address(seed = self.config['tn']['gatewaySeed'])
                amount = transactionInfo['amount'] - self.config['tn']['fee']
                if self.txNotYetExecuted(transaction.hex(), dbCon):
                    try:
                        addr = pw.Address(targetAddress)
                        tx = tnAddress.sendAsset(pw.Address(targetAddress), pw.Asset(self.config['tn']['assetId']), int(amount * 10 ** self.config['tn']['decimals']), '', '', 2000000)
                        print("sended tx"+str(tx))
                    except Exception as e:
                        tx = {"id":"invalid attachment"}
                        print('invalid attachment')                    
                    dateTimeObj = datetime.datetime.now()
                    timestampStr = dateTimeObj.strftime("%d-%b-%Y (%H:%M:%S.%f)")
                    cursor.execute('INSERT INTO executed ("sourceAddress", "targetAddress", "tnTxId", "ethTxId", "timestamp", "amount", "amountFee") VALUES ("' + transactionInfo['sender'] + '", "' + targetAddress + '", "' + tx['id'] + '", "' + transaction.hex() + '", "' + timestampStr +  '", "' + str(amount) + '", "' + str(self.config['tn']['fee']) + '")')
                    cursor.execute('DELETE FROM tunnel WHERE sourceAddress ="' + transactionInfo['sender'] + '" AND targetAddress = "' + targetAddress + '"')
                    dbCon.commit()
                    print('incomming transfer completed')

    def txNotYetExecuted(self, transaction, dbCon):
        cursor = dbCon.cursor()
        result = cursor.execute('SELECT tnTxId FROM executed WHERE ethTxId = "' + transaction + '"').fetchall()

        return len(result) == 0

    def checkIfTransacitonValid(self, transactionInfo):
        return transactionInfo != None and \
               transactionInfo['function'] == 'transfer' and \
               transactionInfo['recipient'] == self.config['erc20']['gatewayAddress'] and \
               transactionInfo['token'] == self.config['erc20']['contract']['address']
