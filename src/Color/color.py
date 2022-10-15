class Color:
    def red(self, text):
        return "\033[31m%s\033[0m" % text
    
    def green(self, text):
        return "\033[32m%s\033[0m" % text 