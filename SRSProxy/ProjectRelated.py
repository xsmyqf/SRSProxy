import requests,json
from HelperTools import Debug
import os


sourceStreamInfoListUrl = os.getenv('SourceStream')
GetNotFixedStreamAPIUrl = os.getenv("NotFixedStreamAPI")



# 需要做代理的源流信息
sourceStreamInfoList = {}

def GetSourceStreamInfoList():
    if sourceStreamInfoListUrl == None or sourceStreamInfoListUrl == "default_source_stream_url":
        Debug.Log("SourceStream is null,so return GetSourceStreamInfoList")
        return
    resultData = requests.get(sourceStreamInfoListUrl)
    resultJson = json.loads(resultData.text)
    sourceStreamInfoList.clear()
    for oneStream in resultJson:
        sourceStreamInfoList[oneStream["url"]] = {}
        sourceStreamInfoList[oneStream["url"]]["bFixedUrl"] = bool(int(oneStream["FIXEDURL"]))
        sourceStreamInfoList[oneStream["url"]]["url"] = oneStream["CAMERAINDEXCODE"]
    Debug.Log(f"GetSourceStreamInfoList:{sourceStreamInfoList}")
    return sourceStreamInfoList

GetSourceStreamInfoList()

def GetUnFixedUrl(UnFixedStreamUrl):
    if GetNotFixedStreamAPIUrl == None or GetNotFixedStreamAPIUrl == "default_notfixed_stream_url":
        Debug.Log("NotFixedStreamAPI is null,so return GetUnFixedUrl")
        return None
    requestData = {
        "url": UnFixedStreamUrl
    }
    resultData = requests.get(GetNotFixedStreamAPIUrl, params=requestData)
    resultJson = json.loads(resultData.text)
    if int(resultJson["code"]) == 0 and resultJson["msg"] == "success":
        return resultJson["data"]["url"]