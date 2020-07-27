import time
import traceback
import sharedfunc
from dbClass import dbCalls
from tnClass import tnCalls
from otherClass import otherCalls
from etherscanClass import etherscanCalls
from verification import verifier

class ETHChecker(object):
    def __init__(self, config):
        self.config = config
        self.db = dbCalls(config)
        self.tnc = tnCalls(config)
        self.verifier = verifier(config)

        if self.config['erc20']['etherscan-on']:
            self.otc = etherscanCalls(config)
        else:
            self.otc = otherCalls(config)

        self.lastScannedBlock = self.db.lastScannedBlock("ETH")

    def run(self):
        #main routine to run continuesly
        #print('INFO: started checking ETH blocks at: ' + str(self.lastScannedBlock))

        while True:
            try:
                nextblock = self.otc.currentBlock() - self.config['erc20']['confirmations']

                if nextblock > self.lastScannedBlock:
                    if self.config['erc20']['etherscan-on']:
                        self.checkBlock(self.lastScannedBlock)
                        self.db.updHeights(nextblock, "ETH")
                        self.lastScannedBlock = self.db.lastScannedBlock("ETH")
                    else:
                        self.lastScannedBlock += 1
                        self.checkBlock(self.lastScannedBlock)
                        self.db.updHeights(self.lastScannedBlock, "ETH")
            except Exception as e:
                self.lastScannedBlock -= 1
                print('ERROR: Something went wrong during ETH block iteration: ' + str(traceback.TracebackException.from_exception(e)))

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
                            self.db.updTunnel("error", sourceAddress, targetAddress, statusOld='created')
                        else:
                            try:
                                self.db.updTunnel("sending", sourceAddress, targetAddress, statusOld='created')
                                tx = self.tnc.sendTx(targetAddress, amount, 'Thanks for using our service!')

                                if 'error' in tx:
                                    self.faultHandler(txInfo, "senderror", e=tx['message'])
                                else:
                                    print("INFO: send tx: " + str(tx))

                                    self.db.insExecuted(txInfo['sender'], targetAddress, txInfo['id'], tx['id'], amountCheck, self.config['tn']['fee'])
                                    print('INFO: send tokens from eth to tn!')

                                    #self.db.delTunnel(txInfo['sender'], targetAddress)
                                    self.db.updTunnel("verifying", sourceAddress, targetAddress, statusOld="sending")
                            except Exception as e:
                                self.db.updTunnel("error", sourceAddress, targetAddress, statusOld="sending")
                                self.faultHandler(txInfo, "txerror", e=e)

                            if len(tx) == 0:
                                #TODO
                                self.db.insError(sourceAddress, targetAddress, '', txInfo['id'], amountCheck, 'tx failed to send - manual intervention required')
                                print("ERROR: tx failed to send - manual intervention required")
                                self.db.updTunnel("error", sourceAddress, targetAddress, statusOld="sending")
                            else:
                                self.tnc.verifyTx(tx, sourceAddress, targetAddress)

                            
        
    def faultHandler(self, tx, error, e=""):
        #handle transfers to the gateway that have problems
        amount = tx['amount']
        timestampStr = sharedfunc.getnow()

        if error == "notunnel":
            self.db.insError(tx['sender'], '', '', tx['id'], amount, 'no tunnel found for sender')
            print("ERROR: " + timestampStr + " - Error: no tunnel found for transaction from " + tx['sender'] + " - check errors table.")

        if error == "txerror":
            targetAddress = tx['recipient']
            self.db.insError(tx['sender'], targetAddress, '', tx['id'], amount, 'tx error, possible incorrect address', str(e))
            print("ERROR: " + timestampStr + " - Error: on outgoing transaction for transaction from " + tx['sender'] + " - check errors table.")

        if error == "senderror":
            targetAddress = tx['recipient']
            self.db.insError(tx['sender'], targetAddress, '', tx['id'], amount, 'tx error, check exception error', str(e))
            print("ERROR: " + timestampStr + " - Error: on outgoing transaction for transaction from " + tx['sender'] + " - check errors table.")
