"""
@Author: Kowaine
@Description: 简单的http服务器
@Date: 2021-01-03 21:59:24
@LastEditTime: 2021-01-12 21:29:12
"""

import base
from urllib.parse import urlparse, parse_qs, quote
import json
import socket

class HTTPRequest(base.Request):
    """
    解析http请求的类
    """
    def __init__(self, content, addr):
        super().__init__(content.decode(), addr)

    @property
    def method(self):
        """
        请求方法
        """
        return self.content.split()[0]

    @property
    def path(self):
        """
        请求路径
        """
        return self.content.split()[1]

    @property
    def body(self):
        return self.content.split("\r\n\r\n", 1)[1]

    @property
    def query(self):
        """
        url参数, query形式
        """
        query = urlparse(self.path).query
        return query

    @property
    def params(self):
        """
        url参数, 字典形式
        """
        params = parse_qs(self.query) 
        return params
    @property
    def headers(self):
        """
        请求头
        """
        headers_lines = self.content.split("\r\n\r\n", 1)[0].split("\r\n")[1:]
        headers = {}
        for line in headers_lines:
            key, value = line.split(": ")
            # 编码成%xx的形式，防止乱码
            headers[quote(key)] = quote(value)
            # headers[key] = value
        return headers

    def __str__(self):
        return self.content

    
class EasyServer(base.BaseServer):
    """
    一个简单的http服务器
    """
    def __init__(self, host, port, max_connection=1024, request_model=HTTPRequest, use_ipv6=False):
        """
        重写父类初始化函数，更换请求类的默认模板
        @args:
            host 主机ip :string
            port 监听端口 :int
            max_connection 最大连接数 :int
            request_model 请求处理模板 :type
        """
        super().__init__(host, port, max_connection, request_model, use_ipv6)

    def process_request(self, request):
        """
        重写处理请求的函数，将请求相关数据用json格式返回
        """
        response_body = {}
        # response_body["from"] = request.addr
        # response_body["method"] = request.method
        # response_body["path"] = request.path
        # response_body["query"] = request.query
        # response_body["headers"] = request.headers
        # response_body["body"] = request.body
        response_headers = "HTTP/1.1 200 OK\r\nContent-Type: text/json\r\n\r\n"
        response = response_headers + json.dumps(response_body)
        return response

    def preprocess_request(self, connection, addr, chunk=512, timeout=0.5):
        """
        将流式的请求数据处理为Request
        @args:
            connection 连接的socket, 由socket.accept()得到 :socket
            addr 发来连接的地址 :string
            chunk 流式数据的分块大小 :int
            timeout 定义一个时长timeout，当timeout秒后不再接收到数据，就认为数据已经传输完毕 :number
        """
        content = b""
        connection.settimeout(timeout)
        while True:
            try:
                temp = connection.recv(chunk)
                if temp:
                    content += temp
            except socket.timeout:
                if content.endswith(b"\r\n\r\n"):
                    break
        
        # content为空则为空请求，或者连接已经断开，不再继续解析请求
        if not content:
            return None
        return self.request_model(content, addr)
        

IS_EXAMPLE = False
if __name__ == "__main__" and IS_EXAMPLE:
    server = EasyServer("127.0.0.1", 8000)
    server.serve("EasyServer开始运行!\n\n")
