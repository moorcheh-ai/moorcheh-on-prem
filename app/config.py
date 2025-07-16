import os
class Config:
    DEBUG = True
    HOST = "0.0.0.0"
    PORT = 8000
    CUR= os.getcwd()
    LOG_FILE = os.path.join(os.getcwd(), "logs", "server.log")
    METRICS_ENDPOINT = "/metrics"
