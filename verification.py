from dbClass import dbCalls
from dbPGClass import dbPGCalls
from tnClass import tnCalls
from otherClass import otherCalls
from etherscanClass import etherscanCalls

class verifier(object):
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

        if self.config['other']['etherscan-on']:
            self.otc = etherscanCalls(config, self.db)
        else:
            self.otc = otherCalls(config, self.db)

    def checkTX(self, targetAddress = '', sourceAddress = ''):
        result = {'status': '', 'tx': '', 'block': '', 'error': ''}

        if targetAddress != '':
            address = targetAddress
        elif  sourceAddress != '':
            address = sourceAddress
        else:
            result['status'] = 'error'
            result['error'] = 'invalid address'
            return result

        if not self.tnc.validateAddress(address):
            result['status'] = 'error'
            result['error'] = 'invalid address'
            return result
        else:
            tx = self.db.getTunnelStatus(targetAddress=address)

            if len(tx) != 0:
                result['status'] = tx[0][0]
                
                if result['status'] == "sending" or result['status'] == "verifying":
                    resexec = self.checkExecuted(targetAddress=targetAddress, sourceAddress=sourceAddress)

                    if 'error' in resexec:
                        result['error'] = resexec['error']
                    else:
                        result['tx'] = resexec['tx']
                        result['block'] = resexec['block']
                elif result['status'] == "created":
                    return result
                elif result['status'] == "error":
                    resexec = self.db.getError(targetAddress=targetAddress, sourceAddress=sourceAddress)

                    if len(resexec) != 0:
                        result['error'] = resexec[0][0]
                        if targetAddress != '':
                            result['tx'] = resexec[0][2]
                        else:
                            result['tx'] = resexec[0][1]
            else:
                resexec = self.checkExecuted(targetAddress=targetAddress, sourceAddress=sourceAddress)

                if 'error' in resexec:
                    result['error'] = resexec['error']
                else:
                    result['tx'] = resexec['tx']
                    result['block'] = resexec['block']

        return result

    def checkExecuted(self, targetAddress = '', sourceAddress = ''):
        if targetAddress != '':
            tx = self.db.getExecuted(targetAddress=targetAddress)
        elif  sourceAddress != '':
            tx = self.db.getExecuted(sourceAddress=sourceAddress)
        else:
            return {'error': 'invalid address'}
        
        if len(tx) == 0:
            return {'error': 'no tx found'}
        else:
            tx = tx[0][0]
            result = self.db.getVerified(tx)

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

        #if (self.config["main"]["max"] * 10) > balanceOther > 0: total += 100
        #if (self.config["main"]["max"] * 10) > balanceTN > 0: total += 100

        #if numErrors == 0: total += 100
        if numErrors < 10: total += 100

        if not connTN or not connOther:
            status = "red"
        elif total == 500:
            status = "green"
        else:
            status = "yellow"
        
        result = {
            "chainName": self.config['main']['name'],
            "assetID": self.config['tn']['assetId'],
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
                current = self.otc.currentBlock() - self.config["other"]["confirmations"]
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

