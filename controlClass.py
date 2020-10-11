import time
import traceback
import sharedfunc
from dbClass import dbCalls
from dbPGClass import dbPGCalls
from tnClass import tnCalls
from otherClass import otherCalls
from etherscanClass import etherscanCalls
from verification import verifier

class controller(object):
    def __init__(self, config, db = None):
        self.config = config

        if db == None:
            if self.config['main']['use-pg']:
                self.db = dbPGCalls(config)
            else:
                self.db = dbCalls(config)
        else:
            self.db = db

        self.tnc = tnCalls(config, self.db)
        self.verifier = verifier(config, self.db)

        if self.config['other']['etherscan-on']:
            self.otc = etherscanCalls(config, self.db)
        else:
            self.otc = otherCalls(config, self.db)

    def run(self):
        #main routine to run continuesly
        print("INFO: starting controller")

        #handle unverified tx
        to_verify = self.db.getUnVerified()

        if len(to_verify) > 0:
            for txV in to_verify:

                if txV[1] != 'TN':
                    print("INFO: verify tx: " + txV[2])
                    tx = txV[2]
                    self.otc.verifyTx(tx)
                else:
                    print("INFO: verify tx: " + txV[2])
                    tx = {'id': txV[2]}
                    self.tnc.verifyTx(tx)

        while True:
            #print("INFO: Last scanned ETH block: " + str(self.db.lastScannedBlock("ETH")))
            #print("INFO: Last scanned TN block: " + str(self.db.lastScannedBlock("TN")))

            #handle tunnels on status 'verifying'
            to_verify = self.db.getTunnels(status='verifying')

            if len(to_verify) > 0:
                for address in to_verify:
                    sourceAddress = address[0]
                    targetAddress = address[1]

                    if self.otc.validateAddress(sourceAddress):
                        txid = self.db.getExecuted(targetAddress=targetAddress)
                        print("INFO: verify tx: " + txid[0][0])
                        tx = {'id': txid[0][0]}
                        self.tnc.verifyTx(tx, sourceAddress, targetAddress)
                    else:
                        txid = self.db.getExecuted(sourceAddress=sourceAddress)
                        print("INFO: verify tx: " + txid[0][0])
                        tx = txid[0][0]
                        self.otc.verifyTx(tx, sourceAddress, targetAddress)

            #TODO: handle tunnels on status 'sending'
            time.sleep(600)