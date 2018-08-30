# this is a simplified version of the standard Python logging module
class Logger():
   name = ""
   def __init__(self, name):
      self.name = name
   def error(self, msg, *args, **kwargs):
      print(self.name, 'error', msg % args)
   def warning(self, msg, *args, **kwargs):
      print(self.name, 'warning', msg % args)
   def debug(self, msg, *args, **kwargs):
      print(self.name, 'debug', msg % args)
   def info(self, msg, *args, **kwargs):
      print(self.name, 'info', msg % args)

def getLogger(x):
    return Logger(x)


