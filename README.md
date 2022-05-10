# SRS流代理

## 需求背景

有的时候我们需要把一些散着的流集中起来管理，然后推向SRS服务器。比如一堆摄像头，但是摄像头的流并不是一直需要打开的，这个时候我们希望这个流管理是动态的，在需要的时候打开，以上就是SRS流代理的出现背景。

## 原理

1. 程序启动时有一个源流列表，每个流有两个主要信息，该流是否是动态url(有些摄像头的url是动态的)，url地址。该流可通过API获取，也可以直接写在文件里。
2. 运行时维护一个流的列表，这个列表里的流有很多状态，比如关闭，打开，等待打开，等待关闭等等，不同状态之间的转换是有前提的，有两个主要API：创建流和删除流。创建流时在列表里添加流，并启动ffmpeg进行推流。

## 特点

该SRS流代理有几个特点：

1. 能够动态创建新流，并把新流放到源流列表里。
2. 能够关闭闲置的推流，比如当没有客户端从SRS拉流时过多少时间，就把该推流关闭。
3. 能够断流重连，它会一直检查SRS的该流状态，如果已经断开，则重新开启流。
4. 能够记录从SRS主动拉起流，当SRS的一个流没有流时，如果它在SRS流代理的源流列表里，则主动拉起。

## 快速上手

可以使用docker快速上手：

```yml
version: '3'
services:
  srs:
    image: codingspace-docker.pkg.coding.net/autoscript/public_image/srs
    user: root
    ports:
      - 8220:1935
      - 8230:1985
      - 8080:8080
    restart: always
  srs_proxy:
    image: codingspace-docker.pkg.coding.net/autoscript/public_image/srsproxy
    ports:
      - 8600:5000
    environment:
      - SourceStream=获取摄像头列表API，如果没有可为空。
      - NotFixedStreamAPI=动态获取摄像头URL的API，如果没有可为空。
      - KeepConnectTime=900 可不填，默认是900
      - TargetStreamUrlPrefix=rtmp://srs:1935/live/
      - TargetStreamAPIUrl=http://srs:1985/api/v1/streams
    restart: always
```

注意：

1. SourceStream是获取源摄像头列表的API，当然该摄像头列表可以是静态的，可以在ProjectRelated.py中写死：

   ```python
   sourceStreamInfoList={
       streamName1:{"url":"rtmp://...","bFixedUrl":True},
       streamName2:{"url":"rtmp://...","bFixedUrl":False},
       streamName3:{"url":"rtmp://...","bFixedUrl":True},
   }
   ```

2. NotFixedStreamAPI该API主要是用来获取摄像头动态Url的，比如海康的摄像头。
3. ProjectRelated.py中的两个函数都是可以根据实际的API来进行修改的，只要保证sourceStreamInfoList的结构跟上面的是一样的就OK。

## Q&A

### 提Issue

如果要提Issue的话，请把问题出现的情况以及复现问题的操作详细陈述下，并把Log贴一下，相关Log可通过GetServerLog的API来获取。

## API

该程序的API均为Get方法请求。

### AddStreamProxy

创建流

1. 如果源流列表里有该流的Url，只需提供流名称即可。
2. 如果源流列表里没有该流的Url，需要提供流的Url。它会把新流放入源流列表里。

下面为相关参数：

参数名 | 参数含义 | 默认值 | 必须指定 | 可取值
--- | --- | --- | --- | ---
targetStreamName | 目标流名字 | 无 | 是 | -
sourceStreamUrl | 源流url | 无 | 否 | -
recreate | 是否重新创建该流 | 0 | 否 | 0,1
retrynum | 如果一个流推流失败，要重试几次 | 3 | 否 | 数字
waitSRSTime | 创建流时等待的时间 | 12 | 否 | 数字
bFixedUrl | 是否固定Url，需要和sourceStreamUrl搭配使用 | 1 | 否 | 0,1

下面是实例:

1. 创建一个固定Url的新流，创建一次就行，下一次只指定targetStreamName即可：

    > http://targetIp:targetPort/AddStreamProxy?targetStreamName=streamName&bFixedUrl=1&sourceStreamUrl=rtmp://targetip/xiexieshuai

2. 创建一个在源流列表里的流：

    > http://targetIp:targetPort/AddStreamProxy?targetStreamName=streamName  

### GetServerLog

获取日志信息，日志是分两部分的，默认情况下是获取比较新的一部分日志。可以使用参数获取老的日志信息。

参数名 | 参数含义 | 默认值 | 必须指定 | 可取值
--- | --- | --- | --- | ---
bShowOlderFile | 是否显示老的日志信息 | 无 | 否 | -
logFileName | 指定显示哪天的日志信息 | 无 | 否 | -

下面是实例：

1. 获取今天的最新日志：

    > http://targetIp:targetPort/GetServerLog

2. 获取所有旧的日志信息，除了上面的所有旧的日志信息：

    > http://targetIp:targetPort/GetServerLog?bShowOlderFile=1

3. 获取某天的日志信息：

    > http://targetIp:targetPort/GetServerLog?bShowOlderFile=1&logFileName=2022-02-12

### RemoveStreamProxy

删除流，这个只有一个参数，下面直接给实例了：

> http://targetIp:targetPort/RemoveStreamProxy?targetStreamName=streamName

### GetServerInfo

显示当前服务器主要变量：

> http://targetIp:targetPort/GetServerInfo

### GetSourceStreamInfoList

显示源流信息列表：

> http://targetIp:targetPort/GetSourceStreamInfoList

### GetStreamUrl

获取某个流的url

> http://targetIp:targetPort/GetStreamUrl?targetStreamName=streamName

### SetKeepConnectTime

当没有客户端拉取流时，设置超时时间，超过这个时间会关闭推送流

参数名 | 参数含义 | 默认值 | 必须指定 | 可取值
--- | --- | --- | --- | ---
KeepConnectTime | 超时时间 | 900 | 否 | 数字

实例：

> http://targetIp:targetPort/SetKeepConnectTime?KeepConnectTime=900
