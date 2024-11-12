import logging
from datetime import datetime

class fubon_neo_logger():
    def __init__(self, logger_name='fubon_neo', logger_level=logging.DEBUG, log_save_path='./log', log_file_name='fubon_neo'):
        log_formatter = logging.Formatter("%(asctime)s.%(msecs)03d [%(threadName)s] [%(levelname)s]: %(message)s", datefmt = '%Y-%m-%d %H:%M:%S')
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logger_level)
        self.log_path = log_save_path

        today_date = datetime.today()
        today_str = datetime.strftime(today_date, "%Y%m%d")
        self.file_name = "{0}/{1}.log.{2}".format(self.log_path, log_file_name, today_str)

        file_handler = logging.FileHandler(self.file_name, 'a', 'utf-8')
        file_handler.setFormatter(log_formatter)
        self.logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        self.logger.addHandler(console_handler)

        self.logger.info("SDK Logger Init, "+logger_name+" logger created")

    def get_logger(self):
        return self.logger