
import requests
from lxml import etree
import time
from selenium.webdriver import Chrome, ChromeOptions, Edge, EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def google():
    instance = Edge(executable_path='E:/utils/msedgedriver.exe')
    instance.get('https://www.jennyfer.com/fr-fr/vetements/tops-et-t-shirts/crop-top/tee-shirt-moulant-blanc-avec-decoupe-sur-le-devant-10042805255.html')
    wait = WebDriverWait(instance, 15)
    wait.until(EC.visibility_of('body'))
    instance.quit()

