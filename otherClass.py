import os
import traceback
from web3 import Web3
from ethtoken.abi import EIP20_ABI
from dbClass import dbCalls
from dbPGClass import dbPGCalls

class otherCalls(object):
    def __init__(self, config):
        self.config = config

        if self.config['main']['use-pg']:
            self.db = dbPGCalls(config)
        else:
            self.db = dbCalls(config)

        self.w3 = self.getWeb3Instance()
        self.privatekey = os.getenv(self.config['other']['seedenvname'], self.config['other']['privateKey'])

        self.lastScannedBlock = self.db.lastScannedBlock("ETH")

    def getWeb3Instance(self):
        instance = None

        if self.config['other']['node'].startswith('http'):
            instance = Web3(Web3.HTTPProvider(self.config['other']['node']))
        else:
            instance = Web3()

        return instance

    def currentBlock(self):
        result = self.w3.eth.blockNumber

        return result

    def getBlock(self, height):
        return self.w3.eth.getBlock(height)

    def currentBalance(self):
        contract = self.w3.eth.contract(address=self.config['other']['contract']['address'], abi=EIP20_ABI)
        balance = contract.functions.balanceOf(self.config['other']['gatewayAddress']).call()
        balance /= pow(10, self.config['other']['contract']['decimals'])

        return balance

    def normalizeAddress(self, address):
        if self.w3.isAddress(address):
            if self.w3.isChecksumAddress(address):
                return address
            else:
                return self.w3.toChecksumAddress(address)
        else:
            return "invalid address"

    def validateAddress(self, address):
        return self.w3.isAddress(address)

    def verifyTx(self, txId, sourceAddress = '', targetAddress = ''):
        if type(txId) == str:
            txid = txId
        else: 
            txid = txId.hex()

        tx = self.db.getExecuted(ethTxId=txid)

        try:
            verified = self.w3.eth.waitForTransactionReceipt(txid, timeout=120)

            if verified['status'] == 1:
                self.db.insVerified("ETH", txid, verified['blockNumber'])
                print('INFO: tx to eth verified!')

                self.db.delTunnel(sourceAddress, targetAddress)
            elif verified['status'] == 0:
                print('ERROR: tx failed to send!')
                self.resendTx(txId)
        except:
            self.db.insVerified("ETH", txid, 0)
            print('WARN: tx to eth not verified!')

    def checkTx(self, tx):
        #check the transaction
        result = None
        transaction = self.w3.eth.getTransaction(tx)

        if transaction['to'] == self.config['other']['contract']['address'] and transaction['input'].startswith('0xa9059cbb'):
            transactionreceipt = self.w3.eth.getTransactionReceipt(tx)
            if transactionreceipt['status']:
                contract = self.w3.eth.contract(address=self.config['other']['contract']['address'], abi=EIP20_ABI)
                sender = transaction['from']

                try:
                    decodedInput = contract.decode_function_input(transaction['input'])
                except Exception as e:
                    self.lastScannedBlock = self.db.lastScannedBlock("ETH")
                    print('ERROR: Something went wrong during ETH block iteration at block ' + str(self.lastScannedBlock) + ': ' + traceback.TracebackException.from_exception(e))
                    return result
                
                recipient = decodedInput[1]['_to']
                if recipient == self.config['other']['gatewayAddress']:
                    amount = decodedInput[1]['_value'] / 10 ** self.config['other']['contract']['decimals']

                    if not self.db.didWeSendTx(tx.hex()): 
                        result = { 'sender': sender, 'function': 'transfer', 'recipient': recipient, 'amount': amount, 'token': self.config['other']['contract']['address'], 'id': tx.hex() }

        return result

    def sendTx(self, targetAddress, amount, gasprice = None, gas = None):
        amount -= self.config['other']['fee']
        amount *= pow(10, self.config['other']['contract']['decimals'])
        amount = int(round(amount))

        token = self.w3.eth.contract(address=self.config['other']['contract']['address'], abi=EIP20_ABI)
        nonce = self.w3.eth.getTransactionCount(self.config['other']['gatewayAddress'], 'pending')

        if gasprice == None:
            if self.config['other']['gasprice'] > 0:
                gasprice = self.w3.toWei(self.config['other']['gasprice'], 'gwei')
            else:
                gasprice = int(self.w3.eth.gasPrice * 1.1)

        if gas == None:
            gas = self.config['other']['gas']

        tx = token.functions.transfer(targetAddress, amount).buildTransaction({
            'chainId': 1,
            'gas': gas,
            'gasPrice': gasprice,
            'nonce': nonce
        })
        signed_tx = self.w3.eth.account.signTransaction(tx, private_key=self.privatekey)
        txId = self.w3.eth.sendRawTransaction(signed_tx.rawTransaction)

        return txId

    def resendTx(self, txId):
        if type(txId) == str:
            txid = txId
        else: 
            txid = txId.hex()

        failedtx = self.db.getExecuted(ethTxId=txid)

        if len(failedtx) > 0:
            id = failedtx[0][0]
            sourceAddress = failedtx[0][1]
            targetAddress = failedtx[0][2]
            tnTxId = failedtx[0][3]
            amount = failedtx[0][6]

            self.db.insError(sourceAddress, targetAddress, tnTxId, txid, amount, 'tx failed on network - manual intervention required')
            print("ERROR: tx failed on network - manual intervention required: " + txid)
            self.db.updTunnel("error", sourceAddress, targetAddress, statusOld="verifying")

