
def evaluate_xpath(self, path):
    script = """
    const result = document.evaluate('{path}', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null)
    return result.singleNodeValue
    """.format(path=path)
    return self.driver.execute_script(script)


def string_value_from_xpath(self, path):
    """Use an xpath to return a string value from the
    parsed element"""
    script = """
    const result = document.evaluate('{path}', document, null, XPathResult.ANY_TYPE, null)
    return result.stringValue
    """.format(path=path)
    return self.driver.execute_script(script)
