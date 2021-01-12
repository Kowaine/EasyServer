"""
@Author: Kowaine
@Description: 基于反向代理，处理bilibili番剧请求，结合 解除B站地区限制 油猴脚本使用
@Date: 2021-01-04 19:00:19
@LastEditTime: 2021-01-12 21:25:41
"""

import http_server
from gevent import socket, monkey
import config_reader
from urllib.parse import unquote, urlparse
import pycurl
from io import BytesIO
import sys
import json

monkey.patch_all()

class BiliConfiger(config_reader.Configer):
    # 默认配置
    DEFAULT_CONF = {
        "proxy": {
            "use_proxy": False,
            "server": "127.0.0.1",
            "port": "7890"
        },
        "local": {
            "host": "127.0.0.1",
            "port": "8000",
            "use_ipv6": False
        }
    }
    def use_proxy(self):
        """
        钩子函数，检测是否配置使用代理
        @returns
            True/False :bool
        """
        # 若配置正确，则返回配置项，否则返回默认值
        if "proxy" in self.conf:
            if "use_proxy" in self.conf['proxy']:
                return self.conf['proxy']['use_proxy'].lower() == "true"
        return self.DEFAULT_CONF['proxy']['use_proxy'].lower() == "true"

    def use_ipv6(self):
        """
        钩子函数，检测是否配置使用ipv6
        @returns
            True/False :bool
        """
        # 若配置正确，则返回配置项，否则返回默认值
        if "local" in self.conf:
            if "use_ipv6" in self.conf['local']:
                return self.conf['local']['use_ipv6'].lower() == "true"
        return self.DEFAULT_CONF['local']['use_ipv6'].lower() == "true"

    def get_proxy(self):
        """
        返回配置好的代理服务器信息，否则返回默认值
        @returns
            (server, port) 服务器,端口元组 :tuple(str, int)
        """
        # 默认值
        server = self.DEFAULT_CONF['proxy']['server']
        port = self.DEFAULT_CONF['proxy']['port']

        # 自定义值
        if "server" in self.conf['proxy']:
            server = self.conf['proxy']['server']
        if "port" in self.conf['proxy']:
            port = self.conf['proxy']['port']

        port = int(port)

        return (server, port)


    def get_local(self):
        """
        返回配置好的本地运行地址与端口，否则返回默认值
        @returns
            (host, port) (地址, 端口) :tuple(str, int)
        """
        # 默认值
        host = self.DEFAULT_CONF['local']['host']
        port = self.DEFAULT_CONF['local']['port']

        # 自定义值
        if "host" in self.conf['local']:
            host = self.conf['local']['host']
        if "port" in self.conf['local']:
            port = self.conf['local']['port']

        port = int(port)

        return (host, port)



class BiliProxy(http_server.EasyServer):
    """
    bilibili反向代理服务器
    """
    def __init__(self, host, port):
        cfg = BiliConfiger()
        if cfg.use_ipv6():
            super().__init__(host, port, use_ipv6=True)
        else:
            super().__init__(host, port)
        self.DOMAIN = "api.bilibili.com"
        self.PC_PATH = "/pgc/player/web/playurl"
        self.APP_PATH = "/pgc/player/api/playurl"
        self.TIMEOUT = 5

    def on_receive(self, connection, addr):
        """
        接收到连接时处理
        @args:
            connection 连接socket :socket
            addr 发来连接的地址 :tuple
        """
        request = self.preprocess_request(connection, addr)
        if request:
            sys.stdout.write("开始处理来自{}的请求\r\n".format(addr))
            response = self.process_request(request, connection)
            if response:
                connection.sendall(response.encode())
            sys.stdout.write("处理完毕\r\n")
        connection.close()

    def process_request(self, request, connection):
        ''' 读取请求相关信息 '''
        try:
            if request.headers == {}:
                raise Exception("headers为空")
            request_method = request.method
            request_query = request.query
            if "Referer" in request.headers: 
                request_referer = request.headers['Referer']
            request_headers = request.headers
            request_body = request.body

            ''' 请求重写 '''
            curl = pycurl.Curl()
            
            headers = request_headers
            
            # 清理headers以伪装
            if "Host" in headers: 
                del headers['Host']
            if "User-Agent" in headers: 
                del headers['User-Agent']
            if "Referer" in headers: 
                del headers['Referer']

            #判断接口
            url = self.DOMAIN
            if "platform=android" in request_query:
                request_query = self.APP_PATH + "?" + request_query
                curl.setopt(pycurl.USERAGENT, "Bilibili Freedoooooom/MarkII")
            else:
                request_query = self.PC_PATH + "?" + request_query
                curl.setopt(pycurl.REFERER, request_referer)

            headers_tuple = []
            for k, v in headers.items():
                headers_tuple.append(unquote(k) + ": " + unquote(v))

            # 读取配置，确认是否使用代理
            cgi = BiliConfiger()
            proxies = None
            if cgi.use_proxy():
                host, port = cgi.get_proxy()
                curl.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_HTTP)
                curl.setopt(pycurl.PROXY, host)
                curl.setopt(pycurl.PROXYPORT, port)

            # 配置curl
            url = "https://" + self.DOMAIN + request_query
            curl.setopt(pycurl.TIMEOUT, self.TIMEOUT)
            curl.setopt(pycurl.CUSTOMREQUEST, request_method)
            curl.setopt(pycurl.URL, url)
            curl.setopt(pycurl.HTTPHEADER, headers_tuple)
            curl.setopt(pycurl.POSTFIELDS, request_body)
            curl.setopt(pycurl.HEADER, True)
            curl.setopt(pycurl.FOLLOWLOCATION, False) # 禁用重定向
            curl.setopt(pycurl.SSL_VERIFYHOST, False) # 禁用https验证
            curl.setopt(pycurl.SSL_VERIFYPEER, False)
            # curl.setopt(pycurl.SSL_VERIFYRESULT, False)
            curl.setopt(pycurl.SSL_VERIFYSTATUS, False)
            curl.setopt(pycurl.VERBOSE, False) # 禁用某些汇报信息
            curl.setopt(pycurl.ENCODING, "utf-8")
            
            # python3必须使用byteio
            result_reader = BytesIO()
            curl.setopt(pycurl.WRITEFUNCTION, result_reader.write)

            # 发送请求
            try:
                curl.perform()
            except pycurl.error as e:
                result_reader.close()
                curl.close()
                raise e

            ''' 处理返回数据 '''
            #获取头部长度
            header_length = curl.getinfo(pycurl.HEADER_SIZE)

            response = result_reader.getvalue()

            # 截取body并计算Content-Length
            response_body = response[header_length:]
            content_length = len(response_body)

            # 截取headers
            response_headers =  response[0:header_length].decode().split("\r\n")[2:-2]

            result_reader.close()
            curl.close()
            
            ''' 返回数据 '''
            # 响应行
            status_string = response_headers[0] + "OK\r\n"
            connection.send(status_string.encode())

            # headers行
            for line in response_headers[1:]:
                header_string = line + "\r\n"
                # 改chunk传输为正常传输(因为Content-Length已知)
                if "chunked" in line:
                    header_string = "Content-Length: " + str(content_length) + "\r\n"
                # 去掉gzip
                elif "gzip" in line:
                    continue    
                connection.sendall(header_string.encode())
            connection.send("\r\n".encode())

            # body行
            response_json =  json.loads(unquote(response_body))
            if "durl" in response_json:
                response_domain = response_json['durl'][0]['url'].split("//", 1)[1].split("/", 1)[0]
                sys.stdout.write("解析得到的服务器域名为：" + response_domain + "\r\n")
            else:
                sys.stdout.write("获取错误：" + unquote(response_body) + "\r\n")
            connection.send(response_body)
            return "\r\n\r\n"
                
        except Exception as e:
            sys.stderr.write(str(e) + "\r\n")
            raise e

    def serve(self, start_msg=''):
        return super().serve(start_msg="\r\nBiliBili反向代理启动!\r\n\r\n")
            
        
if __name__ == "__main__":
    cgi = BiliConfiger()
    host, port = cgi.get_local()
    server = BiliProxy(host, port)
    server.serve()
