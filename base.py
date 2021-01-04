"""
@Author: Kowaine
@Description: 一些基础的数据结构和类型
@Date: 2021-01-03 22:25:39
@LastEditTime: 2021-01-04 04:45:28
"""
from gevent import socket, monkey
import sys
import gevent

monkey.patch_all()

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
            max_connection 最大连接数 :int
            request_model 请求处理模板 :type
        """
        self.host = host
        self.port = port
        self.max_connection = max_connection
        self.server = socket.socket()
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        self.server.bind((host, port))
        self.request_model = request_model

    def run(self):
        """
        启动服务器
        """
        self.server.listen(self.max_connection)
        while True:
            conn, addr = self.server.accept()
            gevent.spawn(self.on_receive, conn, addr)

    def on_receive(self, connection, addr):
        """
        接收到连接时处理
        @args:
            connection 连接socket :socket
            addr 发来连接的地址 :tuple
        """
        request = self.preprocess_request(connection, addr)
        if request:
            response = self.process_request(request)
            connection.sendall(response.encode())
        connection.close()
    
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
                break
        
        # content为空则为空请求，或者连接已经断开，不再继续解析请求
        if not content:
            return None
        return self.request_model(content, addr)

    def process_request(self, request):
        """
        处理request
        @args:
            request 请求 :Request
        """
        return ""

    def serve(self, start_msg=""):
        """
        服务器运行的重写用法
        """
        try:
            sys.stdout.write(start_msg)
            sys.stdout.flush()
            self.run()
        except KeyboardInterrupt:
            sys.exit(0)

    
# 测试用标识符，置为True启用
IS_EXAMPLE = False
if __name__ == "__main__" and IS_EXAMPLE:
    server = BaseServer("127.0.0.1", 8000)
    server.serve("可选的服务器启动信息\n")

