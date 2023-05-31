from selenium.webdriver.common.by import By

class ConditionalXPath:
    def __init__(self, driver, xpath, alternative_xpath, default=None):
        self.result1 = driver.find_element(By.XPATH, xpath)
        self.result2 = driver.find_element(By.XPATH, alternative_xpath)
        self.default = default

        try:
            self.result1 = self.result1.text
        except:
            pass

        try: 
            self.result2 = self.result2.text
        except:
            pass

    def __str__(self):
        return self.result1 or self.result2 or self.default
