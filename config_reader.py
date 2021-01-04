"""
@Author: Kowaine
@Description: 读取与处理配置文件
@Date: 2020-12-26 03:08:46
@LastEditTime: 2021-01-04 19:41:43
"""

import configparser, os


class ConfigException(Exception):
    def __init__(self, config_file):
        self.config_file = config_file
    
    def __str__(self):
        return "配置文件错误 " + self.config_file


    
class Configer():
    """
    配置文件管理类
    """
    # 默认的配置文件
    CONFIG_FILE = "config.ini"
    DEFAULT_CONF = {
    }
    def __init__(self, config_file=CONFIG_FILE):
        self.config_file = config_file
        self.load_config()

    def load_config(self):
        """
        读取配置文件并返回嵌套字典
        """
        cfg = configparser.ConfigParser()
        # print(os.path.join(self.config_file))
        cfg.read(os.path.join(self.config_file), encoding="utf-8")

        conf = {}

        # 遍历section
        for section in cfg.sections():
            # 遍历键值对并重组为字典
            temp_dict = {}
            for item in cfg.items(section):
                temp_dict[item[0]] = item[1]
            conf[section] = temp_dict

        # print(conf)

        self.conf = conf
    
    def reload_config(self, config_file=None):
        """
        重新加载配置文件(可能用不上)
        """
        if config_file:
            self.config_file = config_file
        self.load_config()

