import os
import time
import base58
import PyCWaves
import requests
from dbClass import dbCalls
from dbPGClass import dbPGCalls

class tnCalls(object):
    def __init__(self, config):
        self.config = config

        if self.config['main']['use-pg']:
            self.db = dbPGCalls(config)
        else:
            self.db = dbCalls(config)

        self.node = self.config['tn']['node']

        self.pwTN = PyCWaves.PyCWaves()
        self.pwTN.THROW_EXCEPTION_ON_ERROR = True
        self.pwTN.setNode(node=self.config['tn']['node'], chain=self.config['tn']['network'], chain_id='L')
        seed = os.getenv(self.config['tn']['seedenvname'], self.config['tn']['gatewaySeed'])
        self.tnAddress = self.pwTN.Address(seed=seed)
        self.tnAsset = self.pwTN.Asset(self.config['tn']['assetId'])

    def currentBlock(self):
        result = requests.get(self.node + '/blocks/height').json()['height'] - 1

        return result

    def getBlock(self, height):
        return requests.get(self.node + '/blocks/at/' + str(height)).json()

    def currentBalance(self):
        myBalance = self.tnAddress.balance(assetId=self.config['tn']['assetId'])
        myBalance /= pow(10, self.config['tn']['decimals'])

        return myBalance

    def validateAddress(self, address):
        return self.pwTN.validateAddress(address)

    def verifyTx(self, tx, sourceAddress = '', targetAddress = ''):
        try:
            time.sleep(60)
            verified = self.pwTN.tx(tx['id'])

            if verified['height'] > 0:
                self.db.insVerified("TN", tx['id'], verified['height'])
                print('INFO: tx to tn verified!')

                self.db.delTunnel(sourceAddress, targetAddress)
            else:
                self.db.insVerified("TN", tx['id'], 0)
                print('WARN: tx to tn not verified!')
        except:
            self.db.insVerified("TN", tx['id'], 0)
            print('WARN: tx to tn not verified!')

    def checkTx(self, tx):
        #check the transaction
        if tx['type'] == 4 and tx['recipient'] == self.config['tn']['gatewayAddress'] and tx['assetId'] == self.config['tn']['assetId']:
            #check if there is an attachment
            targetAddress = base58.b58decode(tx['attachment']).decode()
            if len(targetAddress) > 1:
                #check if we already processed this tx
                if not self.db.didWeSendTx(tx['id']): 
                    return targetAddress
            else:
                return "No attachment"

        return None

    def sendTx(self, address, amount, attachment):
        addr = self.pwTN.Address(address)
        if self.config['tn']['assetId'] == 'TN':
            tx = self.tnAddress.sendWaves(addr, amount, attachment, txFee=2000000)
        else:
            tx = self.tnAddress.sendAsset(addr, self.tnAsset, amount, attachment, txFee=2000000)

        return tx