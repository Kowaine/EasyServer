"""
@Author: Kowaine
@Description: 基于反向代理，处理bilibili番剧请求，结合 解除B站地区限制 油猴脚本使用
@Date: 2021-01-04 19:00:19
@LastEditTime: 2021-01-05 05:29:03
"""

import http_server
from gevent import socket, monkey
import config_reader
from urllib.parse import quote, unquote, urlparse
#import ssl
import pycurl
from io import BytesIO
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
            "port": "8000"
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
        super().__init__(host, port)
        self.DOMAIN = "api.bilibili.com"
        self.PC_PATH = "/pgc/player/web/playurl"
        self.APP_PATH = "/pgc/player/api/playurl"
        self.TIMEOUT = 5
        # self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # self.server = ssl.wrap_socket(socket.socket())
        # self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        # self.server.bind((host, port))

    def on_receive(self, connection, addr):
        """
        接收到连接时处理
        @args:
            connection 连接socket :socket
            addr 发来连接的地址 :tuple
        """
        request = self.preprocess_request(connection, addr)
        if request:
            print("开始处理请求")
            response = self.process_request(request, connection)
            if response:
                connection.sendall(response.encode())
            print("处理完毕")
        connection.close()

    def process_request(self, request, connection):
        ''' 读取请求相关信息 '''
        try:
            # print(request.headers)
            if request.headers == {}:
                raise Exception("headers为空")
            # print(request)
            request_method = request.method
            request_query = request.query
            if "Referer" in request.headers: 
                request_referer = request.headers['Referer']
            request_headers = request.headers
            request_body = request.body

            ''' 请求重写 '''
            # request_socket = socket.socket()
            curl = pycurl.Curl()
            
            headers = request_headers
            
            # 清理headers以伪装
            if "Host" in headers: 
                del headers['Host']
            if "User-Agent" in headers: 
                del headers['User-Agent']
            if "Referer" in headers: 
                del headers['Referer']
            # headers['Connection'] = "close"

            #判断接口
            url = self.DOMAIN
            if "platform=android" in request_query:
                # url = self.APP_URL + "?" + request_query
                # url = self.APP_URL
                request_query = self.APP_PATH + "?" + request_query
                # print(request_query)
                # headers['User-Agent'] = "Bilibili Freedoooooom/MarkII"
                curl.setopt(pycurl.USERAGENT, "Bilibili Freedoooooom/MarkII")
            else:
                # url = self.PC_URL + "?" + request_query
                request_query = self.PC_PATH + "?" + request_query
                # if "Referer" in headers: 
                #     headers['Referer'] = request_referer
                curl.setopt(pycurl.REFERER, request_referer)

            # headers_string = ""
            # for k, v in headers.items():
            #     headers_string += unquote(k) + ": " + unquote(v) + "\r\n"
            # headers_string = headers_string.replace("gzip", "")

            headers_tuple = []
            for k, v in headers.items():
                headers_tuple.append(unquote(k) + ": " + unquote(v))

            # 读取配置，确认是否使用代理
            cgi = BiliConfiger()
            proxies = None
            if cgi.use_proxy():
                host, port = cgi.get_proxy()
                # import socks
                # request_socket = socks.socksocket()
                # request_socket.setproxy(socks.PROXY_TYPE_HTTP, host, port)
                curl.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_HTTP)
                curl.setopt(pycurl.PROXY, host)
                curl.setopt(pycurl.PROXYPORT, port)
            
            # request_socket = ssl.wrap_socket(request_socket)

            # 配置curl
            url = "https://" + self.DOMAIN + request_query
            curl.setopt(pycurl.TIMEOUT, self.TIMEOUT)
            curl.setopt(pycurl.CUSTOMREQUEST, request_method)
            curl.setopt(pycurl.URL, url)
            curl.setopt(pycurl.HTTPHEADER, headers_tuple)
            curl.setopt(pycurl.POSTFIELDS, request_body)
            curl.setopt(pycurl.HEADER, True)
            curl.setopt(pycurl.FOLLOWLOCATION, False)
            curl.setopt(pycurl.SSL_VERIFYHOST, False)
            curl.setopt(pycurl.SSL_VERIFYPEER, False)
            curl.setopt(pycurl.VERBOSE, False)
            curl.setopt(pycurl.ENCODING, "utf-8")
            
            # python3必须使用byteio
            result_reader = BytesIO()
            curl.setopt(pycurl.WRITEFUNCTION, result_reader.write)

            curl.perform()
            header_length = curl.getinfo(pycurl.HEADER_SIZE)
            # print(header_length)
            response = result_reader.getvalue()
            # print(response)
            response_body = response[header_length:]
            content_length = len(response_body)
            response_headers =  response[0:header_length].decode().split("\r\n")[2:-2]
            # response_body = gzip.decompress(response_body.encode())
            result_reader.close()
            curl.close()
            
            # 构建返回字符串
            # response_string = ""
            # print(response_headers)
            status_string = response_headers[0] + "OK\r\n"
            connection.send(status_string.encode())
            # print(response_headers)
            for line in response_headers[1:]:
                header_string = line + "\r\n"
                if "chunked" in line:
                    header_string = "Content-Length: " + str(content_length) + "\r\n"
                elif "gzip" in line:
                    continue    
                connection.sendall(header_string.encode())
            connection.send("\r\n".encode())
            # 处理response_body编码问题
            # print(response_body[0])
            connection.send(response_body)
            # print(unquote(response_body))
            return "\r\n\r\n"
                
            # response = b""
            # request_socket.settimeout(self.TIMEOUT)
            # request_socket.connect((url, 443))
            # # 构建请求
            # request_string = \
            #     request_method + " " + request_query + " HTTP/1.1" + "\r\n" \
            #     + headers_string + "\r\n" \
            #     + request_body
            # # print(request_string)
            # request_socket.sendall(request_string.encode())
            # is_first_time = True
            # chunk = 512
            # timeout = 0.5
            # while True:
            #     temp = request_socket.recv(chunk)
            #     if temp:
            #         response += temp
            #         if is_first_time:
            #             request_socket.settimeout(timeout)
            #     else:
            #         break
                
            # print(response)
        except Exception as e:
            print(e)
            raise e
        # finally:
        #     # request_socket.close()
        #     # if response:
        #     #     return response.decode()
        #     # else:
        #     #     return ""
        #     pass

    def serve(self, start_msg=''):
        return super().serve(start_msg="\r\nBiliBili反向代理启动!\r\n\r\n")
            
        
if __name__ == "__main__":
    cgi = BiliConfiger()
    host, port = cgi.get_local()
    server = BiliProxy(host, port)
    server.serve()