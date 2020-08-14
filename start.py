import json
import threading
import uvicorn

from dbClass import dbCalls
from tnClass import tnCalls
from otherClass import otherCalls

from tnChecker import TNChecker
from ethChecker import ETHChecker
from controlClass import controller

with open('config.json') as json_file:
    config = json.load(json_file)

def initialisedb():
    #get current TN block:
    tnlatestBlock = tnCalls(config).currentBlock()
    dbCalls(config).insHeights(tnlatestBlock, 'TN')

    #get current ETH block:
    ethlatestBlock = otherCalls(config).currentBlock()
    dbCalls(config).insHeights(ethlatestBlock, 'ETH')

def main():
    #check db
    dbc = dbCalls(config)

    try:
        result = dbc.lastScannedBlock("TN")

        if not isinstance(result, int):
            if len(result) == 0:
                initialisedb()
    except:
        dbc.createdb()
        initialisedb()

    dbc.createVerify()
    dbc.updateExisting()
        
    #load and start threads
    tn = TNChecker(config)
    eth = ETHChecker(config)
    ctrl = controller(config)
    ethThread = threading.Thread(target=eth.run)
    tnThread = threading.Thread(target=tn.run)
    ctrlThread = threading.Thread(target=ctrl.run)
    ethThread.start()
    tnThread.start()
    ctrlThread.start()
    
    #start app
    uvicorn.run("gateway:app", host="0.0.0.0", port=config["main"]["port"], log_level="warning")

main()
