import re
import sqlite3 as sqlite
from web3 import Web3
from ethtoken.abi import EIP20_ABI
import PyCWaves
import json
from verification import verifier
import datetime
import os

from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.status import HTTP_401_UNAUTHORIZED
import secrets
import uvicorn
from starlette.requests import Request
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBasic()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

with open('config.json') as json_file:
    config = json.load(json_file)

w3 = Web3(Web3.HTTPProvider(config['erc20']['node']))

def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, config["main"]["admin-username"])
    correct_password = secrets.compare_digest(credentials.password, config["main"]["admin-password"])
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

def get_tnBalance():
    pwTN = PyCWaves.PyCWaves()
    pwTN.THROW_EXCEPTION_ON_ERROR = True
    pwTN.setNode(node=config['tn']['node'], chain=config['tn']['network'], chain_id='L')
    seed = os.getenv(config['tn']['seedenvname'], config['tn']['gatewaySeed'])
    tnAddress = pwTN.Address(seed=seed)
    myBalance = tnAddress.balance(assetId=config['tn']['assetId'])
    myBalance /= pow(10, config['tn']['decimals'])
    return int(round(myBalance))

def get_otherBalance():
    contract = w3.eth.contract(address=config['erc20']['contract']['address'], abi=EIP20_ABI)
    balance = contract.functions.balanceOf(config['erc20']['gatewayAddress']).call()
    balance /= pow(10, config['erc20']['contract']['decimals'])
    return int(round(balance))


@app.get("/")
async def index(request: Request):
    heights = await getHeights()
    return templates.TemplateResponse("index.html", {"request": request, 
                                                     "chainName": config['main']['name'],
                                                     "assetID": config['tn']['assetId'],
                                                     "tn_gateway_fee":config['tn']['gateway_fee'],
                                                     "tn_network_fee":config['tn']['network_fee'],
                                                     "tn_total_fee":config['tn']['network_fee']+config['tn']['gateway_fee'],
                                                     "eth_gateway_fee":config['erc20']['gateway_fee'],
                                                     "eth_network_fee":config['erc20']['network_fee'],
                                                     "eth_total_fee":config['erc20']['network_fee'] + config['erc20']['gateway_fee'],
                                                     "fee": config['tn']['fee'],
                                                     "company": config['main']['company'],
                                                     "email": config['main']['contact-email'],
                                                     "telegram": config['main']['contact-telegram'],
                                                     "recovery_amount":config['main']['recovery_amount'],
                                                     "recovery_fee":config['main']['recovery_fee'],
                                                     "ethHeight": heights['ETH'],
                                                     "tnHeight": heights['TN'],
                                                     "tnAddress": config['tn']['gatewayAddress'],
                                                     "ethAddress": config['erc20']['gatewayAddress'],
                                                     "disclaimer": config['main']['disclaimer']})

@app.get('/heights')
async def getHeights():
    dbCon = sqlite.connect('gateway.db')
    result = dbCon.cursor().execute('SELECT chain, height FROM heights WHERE chain = "ETH" or chain = "TN"').fetchall()
    return { result[0][0]: result[0][1], result[1][0]: result[1][1] }

@app.get('/errors')
async def getErrors(request: Request, username: str = Depends(get_current_username)):
    if (config["main"]["admin-username"] == "admin" and config["main"]["admin-password"] == "admin"):
        return {"message": "change the default username and password please!"}
    
    if username == config["main"]["admin-username"]:
        dbCon = sqlite.connect('gateway.db')
        result = dbCon.cursor().execute('SELECT * FROM errors').fetchall()
        return templates.TemplateResponse("errors.html", {"request": request, "errors": result})

@app.get('/executed')
async def getErrors(request: Request, username: str = Depends(get_current_username)):
    if (config["main"]["admin-username"] == "admin" and config["main"]["admin-password"] == "admin"):
        return {"message": "change the default username and password please!"}
    
    if username == config["main"]["admin-username"]:
        dbCon = sqlite.connect('gateway.db')
        result = dbCon.cursor().execute('SELECT * FROM executed').fetchall()
        result2 = dbCon.cursor().execute('SELECT * FROM verified').fetchall()
        return templates.TemplateResponse("tx.html", {"request": request, "txs": result, "vtxs": result2})

@app.get('/ethAddress/{address}')
async def checkTunnel(address):
    dbCon = sqlite.connect('gateway.db')
    address = re.sub('[\W_]+', '', address)
    values = (address,)

    result = dbCon.cursor().execute('SELECT targetAddress FROM tunnel WHERE sourceAddress = ?', values).fetchall()
    if len(result) == 0:
        targetAddress = None
    else:
        targetAddress = result[0][0]

    return { 'sourceAddress': address, 'targetAddress': targetAddress }

@app.get('/tunnel/{sourceAddress}/{targetAddress}')
async def createTunnel(sourceAddress, targetAddress):
    dbCon = sqlite.connect('gateway.db')
    sourceAddress = re.sub('[\W_]+', '', sourceAddress)
    targetAddress = re.sub('[\W_]+', '', targetAddress)

    pwTN = PyCWaves.PyCWaves()
    pwTN.setNode(node=config['tn']['node'], chain=config['tn']['network'], chain_id='L')

    if not pwTN.validateAddress(targetAddress):
        return {'successful': False}

    try:
        sourceAddress = w3.toChecksumAddress(sourceAddress)
    except:
        return { 'successful': False }

    values = (sourceAddress, targetAddress)

    result = dbCon.cursor().execute('SELECT targetAddress FROM tunnel WHERE sourceAddress = ?', (sourceAddress,)).fetchall()
    if len(result) == 0:
        if w3.isAddress(sourceAddress):
            dbCon.cursor().execute('INSERT INTO TUNNEL ("sourceAddress", "targetAddress") VALUES (?, ?)', values)
            dbCon.commit()

            return { 'successful': True }
        else:
            return { 'successful': False }    
    else:
        result = dbCon.cursor().execute('SELECT targetAddress FROM tunnel WHERE sourceAddress = ? AND targetAddress = ?', values).fetchall()
        if len(result) == 0:
            return { 'successful': False }
        else: 
            return { 'successful': True }

@app.get('/deltunnel/{sourceAddress}/{targetAddress}')
async def deleteTunnel(sourceAddress, targetAddress):
    dbCon = sqlite.connect('gateway.db')
    sourceAddress = re.sub('[\W_]+', '', sourceAddress)
    targetAddress = re.sub('[\W_]+', '', targetAddress)

    try:
        sourceAddress = w3.toChecksumAddress(sourceAddress)
    except:
        return { 'successful': False }

    values = (sourceAddress, targetAddress)

    result = dbCon.cursor().execute('SELECT targetAddress FROM tunnel WHERE sourceAddress = ? AND targetAddress = ?', values).fetchall()
    if len(result) == 0:
        return { 'successful': False }
    else: 
        dbCon.cursor().execute('DELETE FROM TUNNEL WHERE sourceAddress = ? AND targetAddress = ?', values)
        dbCon.commit()

        return { 'successful': True }

@app.get('/dustkey/{targetAddress}')
async def createTunnel(targetAddress):
    pwTN = PyCWaves.PyCWaves()
    pwTN.setNode(node=config['tn']['node'], chain=config['tn']['network'], chain_id='L')

    if not pwTN.validateAddress(targetAddress):
        return {'successful': False}

    sourceAddress = str(round(datetime.datetime.now().timestamp()))
    sourceAddress = sourceAddress[-6:]

    dbCon = sqlite.connect('gateway.db')
    values = (sourceAddress, targetAddress)

    result = dbCon.cursor().execute('SELECT targetAddress FROM tunnel WHERE sourceAddress = ?', (sourceAddress,)).fetchall()
    if len(result) == 0:
        result = dbCon.cursor().execute('SELECT sourceAddress FROM tunnel WHERE targetAddress = ?', (sourceAddress,)).fetchall()

        if len(result) == 0:
            dbCon.cursor().execute('INSERT INTO TUNNEL ("sourceAddress", "targetAddress") VALUES (?, ?)', values)
            dbCon.commit()

            return { 'successful': True, 'dustkey': sourceAddress}
        else:
            return { 'successful': True, 'dustkey': result[0][0] }
    else:
        result = dbCon.cursor().execute('SELECT sourceAddress FROM tunnel WHERE sourceAddress = ? AND targetAddress = ?', values).fetchall()
        if len(result) == 0:
            return { 'successful': False }
        else: 
            return { 'successful': True, 'dustkey': result[0][0] }

@app.get("/api/fullinfo")
async def api_fullinfo(request: Request):
    heights = await getHeights()
    tnBalance = get_tnBalance()
    otherBalance = get_otherBalance()
    return {"chainName": config['main']['name'],
            "assetID": config['tn']['assetId'],
            "tn_gateway_fee":config['tn']['gateway_fee'],
            "tn_network_fee":config['tn']['network_fee'],
            "tn_total_fee":config['tn']['network_fee']+config['tn']['gateway_fee'],
            "other_gateway_fee":config['erc20']['gateway_fee'],
            "other_network_fee":config['erc20']['network_fee'],
            "other_total_fee":config['erc20']['network_fee'] + config['erc20']['gateway_fee'],
            "fee": config['tn']['fee'],
            "company": config['main']['company'],
            "email": config['main']['contact-email'],
            "telegram": config['main']['contact-telegram'],
            "recovery_amount":config['main']['recovery_amount'],
            "recovery_fee":config['main']['recovery_fee'],
            "otherHeight": heights['ETH'],
            "tnHeight": heights['TN'],
            "tnAddress": config['tn']['gatewayAddress'],
            "tnColdAddress": config['tn']['coldwallet'],
            "otherAddress": config['erc20']['gatewayAddress'],
            "otherNetwork": config['erc20']['network'],
            "disclaimer": config['main']['disclaimer'],
            "tn_balance": tnBalance,
            "other_balance": otherBalance,
            "minAmount": config['main']['min'],
            "maxAmount": config['main']['max'],
            "type": "tunnel",
            "usageinfo": ""}

@app.get("/api/deposit/{tnAddress}")
async def api_depositCheck(tnAddress):
    checkit = verifier(config)
    result = checkit.checkDeposit(address=tnAddress)

    return result

@app.get("/api/wd/{tnAddress}")
async def api_wdCheck(tnAddress):
    checkit = verifier(config)
    result = checkit.checkWD(address=tnAddress)

    return result

@app.get("/api/checktxs/{tnAddress}")
async def api_checktxs(tnAddress):
    checkit = verifier(config)

    result = checkit.checkTXs(address=tnAddress)

    return result

@app.get("/api/checktxs")
async def api_checktxs():
    checkit = verifier(config)
    result = checkit.checkTXs(address='')

    return result

@app.get('/fees/{fromdate}/{todate}')
async def api_getFees(fromdate, todate):
    checkit = verifier(config)
    result = checkit.getFees(fromdate, todate)

    return result

@app.get('/fees/{fromdate}')
async def api_getFees(fromdate):
    checkit = verifier(config)
    result = checkit.getFees(fromdate, '')

    return result

@app.get('/fees')
async def api_getFees():
    checkit = verifier(config)
    result = checkit.getFees('','')

    return result
