from flask import Flask, request
from ProjectRelated import sourceStreamInfoList
from HelperTools import Debug
from StreamProxy import StreamProxyManager

app = Flask(__name__)

@app.route("/GetServerLog", methods=["GET"])
def GetServerLog():
    bShowOlderFile = bool(int(request.args.get("bShowOlderFile"))) if request.args.get("bShowOlderFile") != None else False
    logFileName = request.args.get("logFileName") if request.args.get("logFileName") != None else None
    return Debug.GetLog(bShowOlderFile,logFileName)

@app.route("/SetKeepConnectTime", methods=["GET"])
def SetKeepConnectTime():
    keepConnectTime = int(request.args.get("KeepConnectTime")) if request.args.get("KeepConnectTime") != None else 900
    return StreamProxyManager.SetKeepConnectTime(keepConnectTime)

@app.route("/GetServerInfo", methods=["GET"])
def GetServerInfo():
    return StreamProxyManager.GetServerInfo()

@app.route("/GetSourceStreamInfoList", methods=["GET"])
def GetSourceStreamInfoList():
    return sourceStreamInfoList


@app.route("/GetStreamUrl", methods=["GET"])
def GetStreamUrl():
    targetStreamName = request.args.get("targetStreamName")
    return StreamProxyManager.GetStreamUrl(targetStreamName)

@app.route("/AddStreamProxy", methods=["GET"])
def AddStreamProxy():
    sourceStreamUrl = request.args.get("sourceStreamUrl")
    targetStreamName = request.args.get("targetStreamName")
    Debug.Log("Enter AddStreamProxyWebWrapper: %s" % targetStreamName)
    bReCreateWhenExist = bool(int(request.args.get("recreate"))) if request.args.get("recreate") != None else False
    TryRecreateNumWhenFail = int(request.args.get("retrynum")) if request.args.get("retrynum") != None else 3
    waitSRSTime = int(request.args.get("waitSRSTime")) if request.args.get("waitSRSTime") != None else 12
    bFixedUrl = bool(int(request.args.get("bFixedUrl"))) if request.args.get("bFixedUrl") != None else True

    return StreamProxyManager.AddStreamProxy(targetStreamName, sourceStreamUrl, bFixedUrl, TryRecreateNumWhenFail, bReCreateWhenExist,waitSRSTime)


@app.route("/RemoveStreamProxy", methods=["GET"])
def RemoveStreamProxy():
    targetStreamName = request.args.get("targetStreamName")
    bStayInList = bool(int(request.args.get("bStayInList"))) if request.args.get("bStayInList") != None else False
    Debug.Log("Enter RemoveStreamProxyWebWrapper: %s,%d" % (targetStreamName, bStayInList))
    return StreamProxyManager.RemoveStreamProxy(targetStreamName, bStayInList)

if __name__ == '__main__':
    app.run(host='0.0.0.0')
