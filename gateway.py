import re
import json
from verification import verifier
from dbClass import dbCalls
from otherClass import otherCalls
from tnClass import tnCalls
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

with open('config_run.json') as json_file:
    config = json.load(json_file)

dbc = dbCalls(config)
tnc = tnCalls(config)
otc = otherCalls(config)

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
    return tnc.currentBalance()

def get_otherBalance():
    return otc.currentBalance()


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
    result = dbc.getHeights()
    return { result[0][0]: result[0][1], result[1][0]: result[1][1] }

@app.get('/errors')
async def getErrors(request: Request, username: str = Depends(get_current_username)):
    if (config["main"]["admin-username"] == "admin" and config["main"]["admin-password"] == "admin"):
        return {"message": "change the default username and password please!"}
    
    if username == config["main"]["admin-username"]:
        result = dbc.getErrors()
        return templates.TemplateResponse("errors.html", {"request": request, "errors": result})

@app.get('/executed')
async def getErrors(request: Request, username: str = Depends(get_current_username)):
    if (config["main"]["admin-username"] == "admin" and config["main"]["admin-password"] == "admin"):
        return {"message": "change the default username and password please!"}
    
    if username == config["main"]["admin-username"]:
        result = dbc.getExecutedAll()
        result2 = dbc.getVerifiedAll()
        return templates.TemplateResponse("tx.html", {"request": request, "txs": result, "vtxs": result2})

@app.get('/ethAddress/{address}')
async def checkTunnel(address):
    address = re.sub('[\W_]+', '', address)

    result = dbc.getTargetAddress(address)
    if len(result) == 0:
        targetAddress = None
    else:
        targetAddress = result

    return { 'sourceAddress': address, 'targetAddress': targetAddress }

@app.get('/tunnel/{sourceAddress}/{targetAddress}')
async def createTunnel(sourceAddress, targetAddress):
    sourceAddress = re.sub('[\W_]+', '', sourceAddress)
    targetAddress = re.sub('[\W_]+', '', targetAddress)

    if not tnc.validateAddress(targetAddress):
        return {'successful': False}

    if not otc.validateAddress(sourceAddress):
        return { 'successful': False }

    sourceAddress = otc.normalizeAddress(sourceAddress)

    result = dbc.getTargetAddress(sourceAddress)
    if len(result) == 0:
        dbc.insTunnel("created", sourceAddress, targetAddress)

        return { 'successful': True }
    else:
        if result != targetAddress:
            return { 'successful': False }
        else: 
            return { 'successful': True }

@app.get('/dustkey/{targetAddress}')
async def createTunnel(targetAddress):
    if not tnc.validateAddress(targetAddress):
        return {'successful': False}

    sourceAddress = str(round(datetime.datetime.now().timestamp()))
    sourceAddress = sourceAddress[-6:]

    result = dbc.getTargetAddress(sourceAddress)
    if len(result) == 0:
        result = dbc.getSourceAddress(targetAddress)

        if len(result) == 0:
            dbc.insTunnel("created", sourceAddress, targetAddress)

            return { 'successful': True, 'dustkey': sourceAddress}
        else:
            return { 'successful': True, 'dustkey': result }
    else:
        result = dbc.getSourceAddress(targetAddress)
        if len(result) == 0:
            return { 'successful': False }
        else: 
            return { 'successful': True, 'dustkey': result }

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
    return dbc.checkTXs(address=tnAddress)

@app.get("/api/checktxs")
async def api_checktxs():
    return dbc.checkTXs(address='')

@app.get('/fees/{fromdate}/{todate}')
async def api_getFees(fromdate, todate):
    return dbc.getFees(fromdate, todate)

@app.get('/fees/{fromdate}')
async def api_getFees(fromdate):
    return dbc.getFees(fromdate, '')

@app.get('/fees')
async def api_getFees():
    return dbc.getFees('','')
