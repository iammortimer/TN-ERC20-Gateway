import time
import traceback
import sharedfunc
from dbClass import dbCalls
from tnClass import tnCalls
from otherClass import otherCalls
from verification import verifier

class ETHChecker(object):
    def __init__(self, config):
        self.config = config
        self.db = dbCalls(config)
        self.otc = otherCalls(config)
        self.tnc = tnCalls(config)
        self.verifier = verifier(config)

        self.lastScannedBlock = self.db.lastScannedBlock("ETH")

    def run(self):
        #main routine to run continuesly
        print('started checking ETH blocks at: ' + str(self.lastScannedBlock))

        while True:
            try:
                nextblock = self.otc.currentBlock() - self.config['erc20']['confirmations']

                if nextblock > self.lastScannedBlock:
                    self.lastScannedBlock += 1
                    self.checkBlock(self.lastScannedBlock)
                    self.db.updHeights(self.lastScannedBlock, "ETH")
            except Exception as e:
                self.lastScannedBlock -= 1
                print('Something went wrong during ETH block iteration: ')
                print(traceback.TracebackException.from_exception(e))

            time.sleep(self.config['erc20']['timeInBetweenChecks'])

    def checkBlock(self, heightToCheck):
        if self.db.doWeHaveTunnels:
            #check content of the block for valid transactions
            block = self.otc.getBlock(heightToCheck)
            for transaction in block['transactions']:
                txInfo = self.otc.checkTx(transaction)

                if txInfo is not None:
                    txContinue = False
                    sourceAddress = txInfo['sender']
                    res = self.db.getTargetAddress(sourceAddress)
                    if len(res) == 0:
                        sourceAddress = str(txInfo['amount'])[-6:]
                        res = self.db.getTargetAddress(sourceAddress)

                        if len(res) == 0:
                            self.faultHandler(txInfo, 'notunnel')
                        else:
                            txContinue = True
                    else:
                        txContinue = True

                    if txContinue:
                        targetAddress = res
                        amount = txInfo['amount']
                        amount -= self.config['tn']['fee']
                        amount *= pow(10, self.config['tn']['decimals'])
                        amount = int(round(amount))

                        amountCheck = amount / pow(10, self.config['tn']['decimals'])
                        if amountCheck < self.config['main']['min'] or amountCheck > self.config['main']['max']:
                            txInfo['recipient'] = targetAddress
                            self.faultHandler(txInfo, "senderror", e='outside amount ranges')
                            #self.db.delTunnel(sourceAddress, targetAddress)
                            self.db.updTunnel("error", sourceAddress, targetAddress)
                        else:
                            try:
                                self.db.updTunnel("sending", sourceAddress, targetAddress)
                                tx = self.tnc.sendTx(targetAddress, amount, 'Thanks for using our service!')

                                if 'error' in tx:
                                    self.faultHandler(txInfo, "senderror", e=tx['message'])
                                else:
                                    print("send tx: " + str(tx))

                                    self.db.insExecuted(txInfo['sender'], targetAddress, transaction.hex(), tx['id'], round(amountCheck), self.config['tn']['fee'])
                                    print('send tokens from eth to tn!')

                                    self.db.delTunnel(txInfo['sender'], targetAddress)
                            except Exception as e:
                                self.faultHandler(txInfo, "txerror", e=e)

                            self.tnc.verifyTx(tx)
        
    def faultHandler(self, tx, error, e=""):
        #handle transfers to the gateway that have problems
        amount = tx['amount']
        timestampStr = sharedfunc.getnow()

        if error == "notunnel":
            self.db.insError(tx['sender'], '', '', tx['id'], amount, 'no tunnel found for sender')
            print(timestampStr + " - Error: no tunnel found for transaction from " + tx['sender'] + " - check errors table.")

        if error == "txerror":
            targetAddress = tx['recipient']
            self.db.insError(tx['sender'], targetAddress, '', tx['id'], amount, 'tx error, possible incorrect address', str(e))
            print(timestampStr + " - Error: on outgoing transaction for transaction from " + tx['sender'] + " - check errors table.")

        if error == "senderror":
            targetAddress = tx['recipient']
            self.db.insError(tx['sender'], targetAddress, '', tx['id'], amount, 'tx error, check exception error', str(e))
            print(timestampStr + " - Error: on outgoing transaction for transaction from " + tx['sender'] + " - check errors table.")
