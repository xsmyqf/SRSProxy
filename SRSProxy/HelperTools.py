import json,datetime
import os
from pathlib import Path

def JsonResult(statecode,msg):
    tempDict = {}
    tempDict["statecode"] = statecode
    tempDict["msg"] = msg
    return json.dumps(tempDict)


class DebugClass:
    # 日志存储结构
    streamOperDebugLog = []

    logNumToSave = 1000

    lastLogSameNum = 0

    lastLogFileName = ""

    logFolder = "SRSStreamProxyLog"

    def __init__(self):
        self.Log("DebugClass init method is called!")
        if not Path(self.logFolder).exists():
            self.Log("created folder:%s" % self.logFolder)
            os.makedirs(self.logFolder)

    def Log(self,info):
        #timeStr = str(time.strftime("%Y-%m-%d %H:%M:%S.%f", time.localtime()))
        logContent = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+"     :      |"+info

        if len(self.streamOperDebugLog) == 0 or self.streamOperDebugLog[-1][self.streamOperDebugLog[-1].find("|")+1:] != info:
            if self.lastLogSameNum != 0 :
                self.streamOperDebugLog.append(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f last message same num:')+"     :      "+str(self.lastLogSameNum))
                self.lastLogSameNum = 0
            self.streamOperDebugLog.append(logContent)
        else:
            self.lastLogSameNum += 1

        print(logContent)

        logFileName = str(datetime.datetime.now().strftime('%Y-%m-%d'))+".txt"

        if len(self.streamOperDebugLog) > self.logNumToSave or (self.lastLogFileName and self.lastLogFileName != logFileName):
            with open(os.path.join(self.logFolder,logFileName), "a") as file:
                for oneLog in self.streamOperDebugLog:
                    file.write(oneLog + "\n")
            self.lastLogFileName = logFileName
            self.streamOperDebugLog.clear()

    def GetLogFile(self,logFileName):
        targetFileName = os.path.join(self.logFolder, logFileName)
        if not Path(targetFileName).exists():
            return "Error: target log file:%s not exist!" % logFileName
        else:
            with open(targetFileName, "r") as f:
                resultTemp = []
                for line in f.readlines():
                    resultTemp.append(line)
                return resultTemp


    def GetLog(self,bShowOlderFile=False,logFileName=None):
        if bShowOlderFile:
            if logFileName != None:
                return json.dumps(self.GetLogFile(logFileName+".txt"))
            else:
                resultList = []

                for root, dirs, files in os.walk(self.logFolder):
                    if len(files) > 0:
                        for oneFile in files:
                            for line in self.GetLogFile(oneFile):
                                resultList.append(line)
                    else:
                        return "not have any log file!"

                return json.dumps(resultList)
        else:
            return json.dumps(self.streamOperDebugLog)


Debug = DebugClass()
