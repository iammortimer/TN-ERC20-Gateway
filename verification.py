from dbCalls import dbCalls
from tnClass import tnCalls

class verifier(object):
    def __init__(self, config):
        self.config = config
        self.db = dbCalls(config)
        self.tnc = tnCalls(config)

    def checkDeposit(self, address):
        if not self.tnc.validateAddress(address):
            return {'error': 'invalid address'}
        else:
            tx = self.db.getExecuted(targetAddress=address)

            if len(tx) == 0:
                return {'error': 'no tx found'}
            else:
                result = self.db.getVerified(tx)

                if len(result) == 0:
                    return {'txVerified': False, 'tx': tx, 'block': 0} 
                else:
                    if result > 0:
                        return {'txVerified': True, 'tx': tx, 'block': result} 
                    else:
                        return {'txVerified': False, 'tx': tx, 'block': result} 

    def checkWD(self, address):
        if not self.tnc.validateAddress(address):
            return {'error': 'invalid address'}
        else:
            tx = self.db.getExecuted(sourceAddress=address)

            if len(tx) == 0:
                return {'error': 'no tx found'}
            else:
                result = result = self.db.getVerified(tx)

                if len(result) == 0:
                    return {'txVerified': False, 'tx': tx, 'block': 0} 
                else:
                    if result > 0:
                        return {'txVerified': True, 'tx': tx, 'block': result} 
                    else:
                        return {'txVerified': False, 'tx': tx, 'block': result} 
