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

        if self.config['erc20']['etherscan-on']:
            self.otc = etherscanCalls(config)
        else:
            self.otc = otherCalls(config)

    def run(self):
        #main routine to run continuesly
        #TODO: check tunnel statusses / verify tx's
        print("INFO: starting controller")