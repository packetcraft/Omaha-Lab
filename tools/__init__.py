from tools.weather import get_weather
from tools.search import web_search
from tools.http_request import http_get
from tools.file_ops import read_file, write_file

TOOLS: list = [get_weather, web_search, http_get, read_file, write_file]
