import json
from dbPGClass import dbPGCalls

with open('config_run.json') as json_file:
    config = json.load(json_file)

dbc = dbPGCalls(config)

lastscannedblock = dbc.lastScannedBlock('TN')
getheights = dbc.getHeights()
doWeHaveTunnels = dbc.doWeHaveTunnels()
getTargetAddress = dbc.getTargetAddress('test')
getSourceAddress = dbc.getSourceAddress('test')
getTunnelStatus = dbc.getTunnelStatus(targetaddress='test')
getTunnels = dbc.getTunnels('created')
checkTXs = dbc.checkTXs('')
checkTXs = dbc.checkTXs('test')
getFees = dbc.getFees('2020-08-01', '2020-10-01')