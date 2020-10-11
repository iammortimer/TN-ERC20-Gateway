import json
import os
import sys
import threading
import uvicorn

from dbClass import dbCalls
from dbPGClass import dbPGCalls
from tnClass import tnCalls
from otherClass import otherCalls

from tnChecker import TNChecker
from ethChecker import ETHChecker
from controlClass import controller

with open('config_run.json') as json_file:
    config = json.load(json_file)

def initialisedb(db):
    #get current TN block:
    tnlatestBlock = tnCalls(config).currentBlock()
    db.insHeights(tnlatestBlock, 'TN')

    #get current ETH block:
    ethlatestBlock = otherCalls(config).currentBlock()
    db.insHeights(ethlatestBlock, 'ETH')

def main():
    #check db
    if config['main']['use-pg']:
        #use PostGres
        dbc = dbPGCalls(config)

        if config["main"]["db-location"] != "":
            path= os.getcwd()
            dbfile = path + '/' + config["main"]["db-location"] + '/' + 'gateway.db'
            dbfile = os.path.normpath(dbfile)
        else:
            dbfile = 'gateway.db'

        if os.path.isfile(dbfile):
            #import old db
            print("INFO: importing old SQLite DB")
            try:
                dbc.importSQLite()
                dbfile_new = dbfile.replace('gateway.db', 'gateway.db.imported')

                os.rename(dbfile, dbfile_new)
            except Exception as e:
                print ('Error %s' % e) 
                print("ERROR: Error occured during import of previous DB")
                sys.exit()
        else:
            try:
                result = dbc.lastScannedBlock("TN")

                if not isinstance(result, int):
                    if len(result) == 0:
                        initialisedb()
            except:
                dbc.createdb()
                initialisedb(dbc)
    else:
        #use SQLite
        dbc = dbCalls(config)

        try:
            result = dbc.lastScannedBlock("TN")

            if not isinstance(result, int):
                if len(result) == 0:
                    initialisedb()
        except:
            dbc.createdb()
            initialisedb(dbc)

        dbc.createVerify()
        dbc.updateExisting()
        
    #load and start threads
    tn = TNChecker(config, dbc)
    eth = ETHChecker(config, dbc)
    ctrl = controller(config, dbc)
    ethThread = threading.Thread(target=eth.run)
    tnThread = threading.Thread(target=tn.run)
    ctrlThread = threading.Thread(target=ctrl.run)
    ethThread.start()
    tnThread.start()
    ctrlThread.start()
    
    #start app
    uvicorn.run("gateway:app", host="0.0.0.0", port=config["main"]["port"], log_level="warning")

main()
