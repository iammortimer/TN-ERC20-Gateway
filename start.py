import sqlite3 as sqlite
import json
import threading
import uvicorn

import setupDB
from tnChecker import TNChecker
from ethChecker import ETHChecker
from controlClass import controller

with open('config_run.json') as json_file:
    config = json.load(json_file)

def main():
    #check db
    try:
        dbCon = sqlite.connect('gateway.db')
        result = dbCon.cursor().execute('SELECT chain, height FROM heights WHERE chain = "TN" or chain = "ETH"').fetchall()
        if len(result) == 0:
            setupDB.initialisedb(config)
    except:
        setupDB.createdb()
        setupDB.initialisedb(config)

    setupDB.createVerify()
    setupDB.updateExisting()
        
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
