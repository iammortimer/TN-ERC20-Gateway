import traceback
from web3 import Web3
from ethtoken.abi import EIP20_ABI
from dbClass import dbCalls

class otherCalls(object):
    def __init__(self, config):
        self.config = config
        self.db = dbCalls(config)
        self.w3 = self.getWeb3Instance()
        self.lastScannedBlock = self.db.lastScannedBlock("ETH")

    def getWeb3Instance(self):
        instance = None

        if self.config['erc20']['node'].startswith('http'):
            instance = Web3(Web3.HTTPProvider(self.config['erc20']['node']))
        else:
            instance = Web3()

        return instance

    def currentBlock(self):
        result = self.w3.eth.blockNumber

        return result

    def getBlock(self, height):
        return self.w3.eth.getBlock(height)

    def currentBalance(self):
        contract = self.w3.eth.contract(address=self.config['erc20']['contract']['address'], abi=EIP20_ABI)
        balance = contract.functions.balanceOf(self.config['erc20']['gatewayAddress']).call()
        balance /= pow(10, self.config['erc20']['contract']['decimals'])

        return int(round(balance))

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

    def verifyTx(self, txId):
        try:
            verified = self.w3.eth.waitForTransactionReceipt(txId.hex(), timeout=120)

            if verified['blockNumber'] > 0:
                self.db.insVerified("ETH", txId.hex(), verified['blockNumber'])
                print('tx to eth verified!')
            else:
                self.db.insVerified("ETH", txId.hex(), 0)
                print('tx to eth not verified!')
        except:
            self.db.insVerified("ETH", txId.hex(), 0)
            print('tx to eth not verified!')

    def checkTx(self, tx):
        #check the transaction
        result = None
        transaction = self.w3.eth.getTransaction(tx)

        if transaction['to'] == self.config['erc20']['contract']['address'] and transaction['input'].startswith('0xa9059cbb'):
            transactionreceipt = self.w3.eth.getTransactionReceipt(tx)
            if transactionreceipt['status']:
                contract = self.w3.eth.contract(address=self.config['erc20']['contract']['address'], abi=EIP20_ABI)
                sender = transaction['from']

                try:
                    decodedInput = contract.decode_function_input(transaction['input'])
                except Exception as e:
                    print('Something went wrong during ETH block iteration at block ' + str(self.lastScannedBlock))
                    print(traceback.TracebackException.from_exception(e))
                    return result
                
                recipient = decodedInput[1]['_to']
                if recipient == self.config['erc20']['gatewayAddress']:
                    amount = decodedInput[1]['_value'] / 10 ** self.config['erc20']['contract']['decimals']

                    if not self.db.didWeSendTx(tx.hex()): 
                        result = { 'sender': sender, 'function': 'transfer', 'recipient': recipient, 'amount': amount, 'token': self.config['erc20']['contract']['address'], 'id': tx.hex() }

        return result

    def sendTx(self, address, amount):
        token = self.w3.eth.contract(address=self.config['erc20']['contract']['address'], abi=EIP20_ABI)
        nonce = self.w3.eth.getTransactionCount(self.config['erc20']['gatewayAddress'])
        if self.config['erc20']['gasprice'] > 0:
            gasprice = self.w3.toWei(self.config['erc20']['gasprice'], 'gwei')
        else:
            gasprice = int(self.w3.eth.gasPrice * 1.1)

        tx = token.functions.transfer(address, amount).buildTransaction({
            'chainId': 1,
            'gas': self.config['erc20']['gas'],
            'gasPrice': gasprice,
            'nonce': nonce
        })
        signed_tx = self.w3.eth.account.signTransaction(tx, private_key=self.privatekey)
        txId = self.w3.eth.sendRawTransaction(signed_tx.rawTransaction)

        return txId
