"""
@Author: Kowaine
@Description: 一些基础的数据结构和类型
@Date: 2021-01-03 22:25:39
@LastEditTime: 2021-01-04 01:13:01
"""
import socket
import asyncio
import sys

class Request(object):
    """
    基础的request结构
    """
    def __init__(self, content, addr):
        self.content = content
        self.addr = addr


class BaseServer():
    def __init__(self, host, port, max_connection=1024, request_model=Request):
        """
        初始化server
        @args:
            host 主机ip :string
            port 监听端口 :int
        """
        self.host = host
        self.port = port
        self.max_connection = max_connection
        self.server = socket.socket()
        self.server.bind((host, port))
        self.request_model = request_model

    async def run(self):
        """
        启动服务器
        """
        self.server.listen(self.max_connection)
        while True:
            conn, addr = self.server.accept()
            request = await self.preprocess_request(conn, addr)
            response = await self.process_request(request)
            conn.sendall(response.encode())
            conn.close()
    
    async def preprocess_request(self, connection, addr, chunk=512, timeout=0.5):
        """
        将流式的请求数据处理为Request
        @args:
            connection 连接的socket, 由socket.accept()得到
            addr 发来连接的地址
            chunk 流式数据的分块大小
            timeout 定义一个时长timeout，当timeout秒后不再接收到数据，就认为数据已经传输完毕
        """
        content = b""
        connection.settimeout(timeout)
        while True:
            try:
                temp = connection.recv(chunk)
                content += temp
            except socket.timeout:
                break
        return self.request_model(content, addr)

    async def process_request(self, request):
        """
        处理request
        """
        return ""

    

    def serve(self, start_msg=""):
        """
        服务器运行的外部简化用法
        """
        sys.stdout.write(start_msg)
        asyncio.run(self.run())

    
# 测试用标识符，置为True启用
IS_EXAMPLE = False
if __name__ == "__main__" and IS_EXAMPLE:
    server = BaseServer("127.0.0.1", 8000)
    server.serve("可选的服务器启动信息\n")

