import time
import traceback
import base58
import sharedfunc
from dbClass import dbCalls
from tnClass import tnCalls
from otherClass import otherCalls
from verification import verifier

class TNChecker(object):
    def __init__(self, config):
        self.config = config
        self.db = dbCalls(config)
        self.otc = otherCalls(config)
        self.tnc = tnCalls(config)
        self.verifier = verifier(config)

        self.lastScannedBlock = self.db.lastScannedBlock("TN")

    def run(self):
        #main routine to run continuesly
        print('started checking tn blocks at: ' + str(self.lastScannedBlock))

        while True:
            try:
                nextblock = self.tnc.currentBlock() - self.config['tn']['confirmations']

                if nextblock > self.lastScannedBlock:
                    self.lastScannedBlock += 1
                    self.checkBlock(self.lastScannedBlock)
                    self.db.updHeights(self.lastScannedBlock, 'TN')
            except Exception as e:
                self.lastScannedBlock -= 1
                print('Something went wrong during tn block iteration: ')
                print(traceback.TracebackException.from_exception(e))

            time.sleep(self.config['tn']['timeInBetweenChecks'])

    def checkBlock(self, heightToCheck):
        #check content of the block for valid transactions
        block = self.tnc.getBlock(heightToCheck)
        for transaction in block['transactions']:
            targetAddress = self.tnc.checkTx(transaction)

            if targetAddress is not None:
                if not(self.otc.validateAddress(targetAddress)):
                    self.faultHandler(transaction, "txerror")
                else:
                    targetAddress = self.otc.normalizeAddress(targetAddress)
                    amount = transaction['amount'] / pow(10, self.config['tn']['decimals'])
                    amount -= self.config['erc20']['fee']
                    amount *= pow(10, self.config['erc20']['contract']['decimals'])
                    amount = int(round(amount))

                    amountCheck = amount / pow(10, self.config['erc20']['contract']['decimals'])
                    if amountCheck < self.config['main']['min'] or amountCheck > self.config['main']['max']:
                        self.faultHandler(transaction, "senderror", e='outside amount ranges')
                    else:
                        try:
                            self.db.insTunnel('sending', transaction['sender'], targetAddress)
                            txId = self.otc.sendTx(targetAddress, amount)

                            if not(str(txId.hex()).startswith('0x')):
                                self.faultHandler(transaction, "senderror", e=txId.hex())
                            else:
                                print("send tx: " + str(txId.hex()))

                                self.db.insExecuted(transaction['sender'], targetAddress, txId.hex(), transaction['id'], round(amountCheck), self.config['erc20']['fee'])
                                self.db.delTunnel(transaction['sender'], targetAddress)
                                print('send tokens from tn to erc20!')
                        except Exception as e:
                            self.faultHandler(transaction, "txerror", e=e)

                        self.otc.verifyTx(txId)
            else:
                self.faultHandler(transaction, 'noattachment')
        
    def faultHandler(self, tx, error, e=""):
        #handle transfers to the gateway that have problems
        amount = tx['amount'] / pow(10, self.config['tn']['decimals'])
        timestampStr = sharedfunc.getnow()

        if error == "noattachment":
            self.db.insError(tx['sender'], "", tx['id'], "", amount, "no attachment found on transaction")
            print(timestampStr + " - Error: no attachment found on transaction from " + tx['sender'] + " - check errors table.")

        if error == "txerror":
            targetAddress = base58.b58decode(tx['attachment']).decode()
            self.db.insError(tx['sender'], targetAddress, tx['id'], "", amount, "tx error, possible incorrect address", str(e))
            print(timestampStr + " - Error: on outgoing transaction for transaction from " + tx['sender'] + " - check errors table.")

        if error == "senderror":
            targetAddress = base58.b58decode(tx['attachment']).decode()
            self.db.insError(tx['sender'], targetAddress, tx['id'], "", amount, "tx error, check exception error", str(e))
            print(timestampStr + " - Error: on outgoing transaction for transaction from " + tx['sender'] + " - check errors table.")
