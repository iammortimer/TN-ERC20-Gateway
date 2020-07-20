from dbClass import dbCalls
from tnClass import tnCalls
from otherClass import otherCalls

class verifier(object):
    def __init__(self, config):
        self.config = config
        self.db = dbCalls(config)
        self.tnc = tnCalls(config)
        self.otc = otherCalls(config)

    def checkDeposit(self, address):
        if not self.tnc.validateAddress(address):
            return {'error': 'invalid address'}
        else:
            tx = self.db.getExecuted(targetAddress=address)

            if len(tx) == 0:
                return {'error': 'no tx found'}
            else:
                result = self.db.getVerified(tx)

                if result is None:
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

                if result is None:
                    return {'txVerified': False, 'tx': tx, 'block': 0} 
                else:
                    if result > 0:
                        return {'txVerified': True, 'tx': tx, 'block': result} 
                    else:
                        return {'txVerified': False, 'tx': tx, 'block': result} 

    def checkHealth(self):
        connTN = self.chConnection('TN')
        connOther = self.chConnection('other')
        heightTN = self.chHeight('TN')
        heightOther = self.chHeight('other')
        balanceTN = self.chBalance('TN')
        balanceOther = self.chBalance('other')
        numErrors = self.chErrors()

        total = 0

        if connTN: total += 100
        if connOther: total += 100

        if heightOther < 100: total += 100
        elif heightOther > 100: total += 50
        if heightTN < 100: total += 100
        elif heightTN > 100: total += 50

        if (self.config["main"]["max"] * 10) > balanceOther > 0: total += 100
        if (self.config["main"]["max"] * 10) > balanceTN > 0: total += 100

        if numErrors == 0: total += 100
        elif numErrors < 10: total += 50

        if not connTN or not connOther:
            status = "red"
        elif total == 700:
            status = "green"
        else:
            status = "yellow"
        
        result = {
            "status": status,
            "connectionTN": connTN,
            "connectionOther": connOther,
            "blocksbehindTN": heightTN,
            "blockbehindOther": heightOther,
            "balanceTN": balanceTN,
            "balanceOther": balanceOther,
            "numberErrors": numErrors
        }

        return result

    def chConnection(self, chain):
        if chain == 'TN':
            try:
                value = self.tnc.currentBlock()
            except:
                value = 0
        else:
            try:
                value = self.otc.currentBlock()
            except:
                value = 0

        if value > 0:
            return True
        else:
            return False

    def chHeight(self, chain):
        if chain == 'TN':
            try:
                current = self.tnc.currentBlock() - self.config["tn"]["confirmations"]
            except:
                current = 0

            lastscanned = self.db.lastScannedBlock("TN")
        else:
            try:
                current = self.otc.currentBlock() - self.config["erc20"]["confirmations"]
            except:
                current = 0

            lastscanned = self.db.lastScannedBlock("ETH")

        if current > 0:
            diff = current - lastscanned
            return diff
        else:
            return -1

    def chBalance(self, chain):
        if chain == 'TN':
            try:
                current = self.tnc.currentBalance()
            except:
                current = 0
        else:
            try:
                current = self.otc.currentBalance()
            except:
                current = 0

        #if current > 0:
            #if current < self.config["main"]["max"]:
            #    return "Too low"
            #elif current > (self.config["main"]["max"] * 10):
            #    return "Too high"
            #else:
            #    return "Good"
        #else:
        #    return "Error"
        return current

    def chErrors(self):
        errors = self.db.getErrors()

        #if len(errors) > 50:
        #    return "Bad"
        #elif 10 < len(errors) < 50:
        #    return "Fair"
        #else:
        #    return "Good"
        
        return len(errors)

