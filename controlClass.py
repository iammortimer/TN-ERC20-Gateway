import time
import traceback
import sharedfunc
from dbClass import dbCalls
from tnClass import tnCalls
from otherClass import otherCalls
from etherscanClass import etherscanCalls
from verification import verifier

class controller(object):
    def __init__(self, config):
        self.config = config
        self.db = dbCalls(config)
        self.tnc = tnCalls(config)
        self.verifier = verifier(config)

        if self.config['other']['etherscan-on']:
            self.otc = etherscanCalls(config)
        else:
            self.otc = otherCalls(config)

    def run(self):
        #main routine to run continuesly
        print("INFO: starting controller")

        while True:
            print("INFO: Last scanned ETH block: " + str(self.db.lastScannedBlock("ETH")))
            print("INFO: Last scanned TN block: " + str(self.db.lastScannedBlock("TN")))

            #handle tunnels on status 'verifying'
            to_verify = self.db.getTunnels(status='verifying')

            if len(to_verify) > 0:
                for address in to_verify:
                    sourceAddress = address[0]
                    targetAddress = address[1]

                    txid = self.db.getExecuted(targetAddress=targetAddress)

                    print("INFO: verify tx: " + txid[0][0])
                    if self.otc.validateAddress(sourceAddress):
                        tx = {'id': txid[0][0]}
                        self.tnc.verifyTx(tx, sourceAddress, targetAddress)
                    else:
                        tx = txid[0][0]
                        self.otc.verifyTx(tx, sourceAddress, targetAddress)
                        
            #TODO: handle tunnels on status 'sending'
            time.sleep(300)