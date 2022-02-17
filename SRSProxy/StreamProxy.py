import subprocess, shlex
import time
from enum import Enum
from apscheduler.schedulers.background import BackgroundScheduler
import json, requests
from ProjectRelated import sourceStreamInfoList, GetUnFixedUrl
from HelperTools import Debug, JsonResult
import os


# 流的状态
# StreamStatusEnum = Enum('StreamStatusEnum', ('WaitForCreate','WaitForKilled','Running','Killed','Broken','Inactive','StartFromSRS','TimeOut','CreatedFailed','NotInConditionList'))
class StreamStatusEnum(Enum):
    WaitForCreate = 0
    WaitForKilled = 1
    Running = 2
    Killed = 3
    Broken = 4
    Inactive = 5
    StartFromSRS = 6
    TimeOut = 7
    CreatedFailed = 8
    NotInConditionList = 9


# 状态之间可转换时的前置状态
StreamStatusCondition = {
    StreamStatusEnum.WaitForCreate: [StreamStatusEnum.Broken, StreamStatusEnum.Inactive,
                                     StreamStatusEnum.CreatedFailed,
                                     StreamStatusEnum.StartFromSRS, StreamStatusEnum.Killed,
                                     StreamStatusEnum.TimeOut,
                                     StreamStatusEnum.NotInConditionList],
    StreamStatusEnum.WaitForKilled: [StreamStatusEnum.Running, StreamStatusEnum.Broken, StreamStatusEnum.Inactive,
                                     StreamStatusEnum.TimeOut],
    StreamStatusEnum.Running: [StreamStatusEnum.WaitForCreate],
    StreamStatusEnum.Killed: [StreamStatusEnum.WaitForKilled],
    StreamStatusEnum.Broken: [StreamStatusEnum.Running, StreamStatusEnum.Killed],
    StreamStatusEnum.Inactive: [StreamStatusEnum.Running, StreamStatusEnum.Killed],
    StreamStatusEnum.StartFromSRS: [StreamStatusEnum.NotInConditionList, StreamStatusEnum.Killed],
    StreamStatusEnum.TimeOut: [StreamStatusEnum.Running],
    StreamStatusEnum.CreatedFailed: [StreamStatusEnum.WaitForCreate]
}


class StreamPorxyClass:
    targetStreamUrlPrefix = os.getenv('TargetStreamUrlPrefix')
    targetStreamAPIUrl = os.getenv('TargetStreamAPIUrl')

    # 当前推送流的管理队列
    streamManagerDict = {}
    # srs服务器的流信息
    serverStreamInfoList = {}
    # srs服务器上每个流的第一次只有一个客户端时的时间，每个一个流长时间只有一个客户端时便超时断开，不再推送。
    streamFirstOneClientTimeDict = {}

    # 代理保持存活的列表,原本用于标识流的状态信息。
    keepConnectList = []

    # 代理保持存活的时间
    keepConnectTime = int(os.getenv('KeepConnectTime'))

    # 检查srs服务器流的健康状态的时间间隔
    CheckSRSStreamHealthyTime = 3

    streamStatusDict = {}

    def __init__(self):
        scheduler = BackgroundScheduler()
        scheduler.add_job(self.CheckSRSStreamHealthy, 'interval', seconds=self.CheckSRSStreamHealthyTime)
        scheduler.start()

    def SetKeepConnectTime(self,timeTemp=900):
        self.keepConnectTime = timeTemp
        return JsonResult(1,"Set Keep Connect Time :%d successfully!" % self.keepConnectTime)

    def GetServerInfo(self):
        resultStr = f'''
            streamManagerDict:{self.streamManagerDict}  \n
            serverStreamInfoList:{self.serverStreamInfoList}  \n
            streamFirstOneClientTimeDict:{self.streamFirstOneClientTimeDict}  \n
            sourceStreamInfoList:{sourceStreamInfoList}  \n
            self.streamStatusDict:{self.streamStatusDict}  \n
            keepConnectList:{self.keepConnectList}  \n
            keepConnectTime:{self.keepConnectTime}  \n
        '''
        return resultStr

    def SetStreamStatus(self,streamName, status):
        if streamName not in self.streamStatusDict:
            if StreamStatusEnum.NotInConditionList in StreamStatusCondition[status]:
                self.streamStatusDict[streamName] = status
                return True
            else:
                Debug.Log(
                    "stream name %s is not in self.streamStatusDict and NotInConditionList is not in %s preview condition" % (
                        streamName, status.name))
                return False
        elif self.streamStatusDict[streamName] in StreamStatusCondition[status]:
            self.streamStatusDict[streamName] = status
            return True
        else:
            Debug.Log("stream name %s current state %s is not in status %s pre condition" % (
                streamName, self.streamStatusDict[streamName].name, status.name))
            return False

    def GetStreamUrl(self,streamName):
        if streamName in sourceStreamInfoList:
            if sourceStreamInfoList[streamName]["bFixedUrl"] == True:
                return sourceStreamInfoList[streamName]["url"]
            if sourceStreamInfoList[streamName]["bFixedUrl"] == False:
                return GetUnFixedUrl(sourceStreamInfoList[streamName]["url"])
        else:
            Debug.Log("streamName: %s not in sourceStreamInfoList!" % streamName)

    def GetSRSStreamState(self):
        resultData = requests.get(self.targetStreamAPIUrl)
        resultJson = json.loads(resultData.text)
        self.serverStreamInfoList.clear()
        for oneStream in resultJson["streams"]:
            self.serverStreamInfoList[oneStream["name"]] = {}
            self.serverStreamInfoList[oneStream["name"]]["clientsnum"] = int(oneStream["clients"])
            self.serverStreamInfoList[oneStream["name"]]["active"] = bool(oneStream["publish"]["active"])
        Debug.Log("GetSRSStreamState:%s" % json.dumps(self.serverStreamInfoList))
        return self.serverStreamInfoList

    def CheckSRSStreamHealthy(self):
        self.GetSRSStreamState()

        if bool(self.serverStreamInfoList):
            for serverStreamName in self.serverStreamInfoList:
                if (serverStreamName not in self.streamManagerDict) and (serverStreamName in sourceStreamInfoList):
                    if self.SetStreamStatus(serverStreamName, StreamStatusEnum.StartFromSRS):
                        Debug.Log("the stream:%s is not in current self.streamManagerDict,start it from srs!" % serverStreamName)
                        self.AddStreamProxy(serverStreamName)

        if not bool(self.streamManagerDict):
            # Debug.Log("not have any push stream,continue check")
            return

        # 以当前字典为准，不以srs的状态列表为准，因为srs的流可能会断
        for streamName in list(self.streamManagerDict.keys()):
            if streamName in self.serverStreamInfoList:
                if (not self.serverStreamInfoList[streamName]["active"]) or (
                        self.serverStreamInfoList[streamName]["clientsnum"] == 0):
                    if self.SetStreamStatus(streamName, StreamStatusEnum.Inactive):
                        Debug.Log("the stream:%s is broken and restart!" % streamName)
                        self.RemoveStreamProxy(streamName)
                        self.AddStreamProxy(streamName)

                if self.serverStreamInfoList[streamName]["clientsnum"] == 1:
                    if streamName in self.keepConnectList:
                        Debug.Log("the stream %s is removed from keepConnectList!" % streamName)
                        self.keepConnectList.remove(streamName)
                        self.streamFirstOneClientTimeDict[streamName] = time.time()
                    else:
                        if streamName not in self.streamFirstOneClientTimeDict:
                            self.streamFirstOneClientTimeDict[streamName] = time.time()
                        else:
                            if (time.time() - self.streamFirstOneClientTimeDict[streamName]) > self.keepConnectTime:
                                if self.SetStreamStatus(streamName, StreamStatusEnum.TimeOut):
                                    Debug.Log("the stream %s 's clients == 1 and timeout!" % streamName)
                                    self.RemoveStreamProxy(streamName)
                                    del self.streamFirstOneClientTimeDict[streamName]

                if self.serverStreamInfoList[streamName]["clientsnum"] > 1:
                    if streamName not in self.keepConnectList:
                        Debug.Log("the stream %s is added to keepConnectList!" % streamName)
                        self.keepConnectList.append(streamName)

            if streamName not in self.serverStreamInfoList:
                # 如果没有在服务器流列表中说明该流已经断流,判断是否需要重连
                if self.SetStreamStatus(streamName, StreamStatusEnum.Broken):
                    Debug.Log("the stream:%s is broken,shutdown it!" % streamName)
                    self.RemoveStreamProxy(streamName)
                    if streamName in self.keepConnectList:
                        Debug.Log("the stream:%s is broken but it is in self.keepConnectList,try to restart it" % streamName)
                        # 需要重新推流
                        self.AddStreamProxy(streamName)

    

    # 1 已经存在，且不重新创建.the stream has been already created!
    # 0 重新创建
    # -1 创建失败
    # -2 在sourceStreamInfoList中找不到targetStreamName的对应url

    def CreateStreamProxy(self,targetStreamName, sourceStreamUrl=None, bFixedUrl=True, bReCreateWhenExist=False,
                          waitSRSTime=12):
        # 如果 sourceStreamUrl不为空，则放入sourceStreamInfoList
        bUseUrlFromSourceStreamInfoList = True
        if not self.SetStreamStatus(targetStreamName, StreamStatusEnum.WaitForCreate):
            return -3

        if sourceStreamUrl != None:
            bUseUrlFromSourceStreamInfoList = False
            if not bFixedUrl:
                sourceStreamUrl = GetUnFixedUrl(sourceStreamUrl)

        if sourceStreamUrl == None:
            sourceStreamUrl = self.GetStreamUrl(targetStreamName)
            if sourceStreamUrl == None:
                return -2

        if targetStreamName in self.streamManagerDict:
            if bReCreateWhenExist:
                self.RemoveStreamProxy(targetStreamName)
            else:
                return 1

        targetStreamUrl = self.targetStreamUrlPrefix + targetStreamName

        Debug.Log(
            "try to push stream info:%s,sourceStreamUrl:%s targetStreamUrl:%s,bReCreateWhenExist:%d,waitSRSTime:%d" % (
            targetStreamName, sourceStreamUrl, targetStreamUrl, bReCreateWhenExist, waitSRSTime))
        cmd_str = f'ffmpeg -i {sourceStreamUrl} -c copy -f flv -flvflags no_duration_filesize {targetStreamUrl}'
        # ret = subprocess.run(cmd_str, encoding="utf-8", shell=True)
        processPtr = subprocess.Popen(shlex.split(cmd_str))

        time.sleep(waitSRSTime)
        # get srs state code
        self.GetSRSStreamState()

        if targetStreamName in self.serverStreamInfoList:
            if self.serverStreamInfoList[targetStreamName]["clientsnum"] >= 1 and self.serverStreamInfoList[targetStreamName]["active"]:
                self.SetStreamStatus(targetStreamName, StreamStatusEnum.Running)
                self.streamManagerDict[targetStreamName] = processPtr

                if not bUseUrlFromSourceStreamInfoList:
                    if targetStreamName not in sourceStreamInfoList:
                        sourceStreamInfoList[targetStreamName] = {}
                    sourceStreamInfoList[targetStreamName]["bFixedUrl"] = bFixedUrl
                    sourceStreamInfoList[targetStreamName]["url"] = sourceStreamUrl

                Debug.Log("create stream %s successfully!:returnCode:%s;polledCode:%s" % (
                    targetStreamName, processPtr.returncode, processPtr.poll()))
                return 0

        Debug.Log("create stream %s falsely!:returnCode:%s;polledCode:%s" % (
            targetStreamName, processPtr.returncode, processPtr.poll()))
        processPtr.kill()
        self.SetStreamStatus(targetStreamName, StreamStatusEnum.CreatedFailed)
        return -1

    def AddStreamProxy(self,targetStreamName, sourceStreamUrl=None, bFixedUrl=True, TryRecreateNumWhenFail=3,
                       bReCreateWhenExist=False, waitSRSTime=12):
        Debug.Log("Enter AddStreamProxy: %s" % targetStreamName)
        while TryRecreateNumWhenFail > 0:
            returnCode = self.CreateStreamProxy(targetStreamName, sourceStreamUrl, bFixedUrl, bReCreateWhenExist,
                                           waitSRSTime)

            if returnCode >= 0:
                return JsonResult(returnCode, "the stream %s is created successfully!" % targetStreamName)
            if returnCode == -2:
                return JsonResult(-2, "the stream %s is not in sourceStreamInfoList" % targetStreamName)
            if returnCode == -3:
                return JsonResult(-3, "the stream %s is not created because some stream is creating!" % targetStreamName)
            if returnCode == -1:
                Debug.Log("try to re create when last time failed,time:%d" % TryRecreateNumWhenFail)
                TryRecreateNumWhenFail -= 1

        return JsonResult(-1,
                          "the stream %s can not be created because srs can not receive push stream info!" % targetStreamName)

    def RemoveStreamProxy(self,targetStreamName, bStayInList=False):
        if not self.SetStreamStatus(targetStreamName, StreamStatusEnum.WaitForKilled):
            return JsonResult(-1, "kill stream %s failed,because of some stream is removing!" % targetStreamName)
        Debug.Log("Enter RemoveStreamProxy: %s,%d" % (targetStreamName, bStayInList))
        if targetStreamName in self.streamManagerDict:
            self.streamManagerDict[targetStreamName].kill()
            time.sleep(3)
            returnCode = self.streamManagerDict[targetStreamName].returncode
            polledCode = self.streamManagerDict[targetStreamName].poll()
            Debug.Log("kill stream %s state:returnCode:%s;polledCode:%s" % (targetStreamName, returnCode, polledCode))
            self.SetStreamStatus(targetStreamName, StreamStatusEnum.Killed)
            if bStayInList == False:
                Debug.Log("stream:%s is removed from self.streamManagerDict" % targetStreamName)
                del self.streamManagerDict[targetStreamName]
            if returnCode == None and polledCode == -9:
                # scheduleList.enter(3,1,removeStreamDelayExecFunc,(targetStreamName,))
                return JsonResult(0, "kill stream %s successed!" % targetStreamName)
            elif returnCode == -9:
                return JsonResult(1, "kill stream %s successed!this stream has been already killed!" % targetStreamName)
            else:
                return JsonResult(2, "kill stream %s successed!returnCode:%s,polledCode:%s" % (
                    targetStreamName, returnCode, polledCode))
        else:
            return JsonResult(3, "%s not in streamDict,no need to kill stream!" % targetStreamName)


StreamProxyManager = StreamPorxyClass()

