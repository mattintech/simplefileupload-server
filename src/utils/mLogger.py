import datetime as dt
import inspect
import os

''' 
 Constants
''' 
LOG_FILE_NAME = "AngelEyes"
LEVEL_INFO = 1
LEVEL_WARNING = 2
LEVEL_ERROR = 3
LEVEL_DEBUG = 4
LEVEL_VERBOSE = 5
DEBUG_LOG_LEVEL = LEVEL_DEBUG


'''
 writeLogMessage(): Write event to text file and to screen depending on log level
 level = int, LEVEL_* constant
 msg = str, Log event message
''' 
def get_caller():
    frames = inspect.stack()
    current_file = os.path.basename(__file__)  # Gets the filename of the logging module
    for frame in frames:
        module_path = frame.filename
        module_name = os.path.basename(module_path)
        # Continue until the module name is not the logger module itself
        if module_name != current_file:
            return module_name.replace('.py', '')
    return "Unknown"

def writeLogMessage(level, msg):

    if DEBUG_LOG_LEVEL == None: 
        raise Exception("mattLog - Specify a Log level. I.e. mattLog.DEBUG_LOG_LEVEL = mattlog.LEVEL_WARNING.")
    if LOG_FILE_NAME == None: 
        raise Exception("mattLog - Specify a Log FileName. I.e. mattLog.LOG_FILE_NAME = \"log.txt\"")

    now = dt.datetime.now()
    y = now.year
    m = now.month
    d = now.day
    caller = get_caller()
    logLevel = levelToString(level)
    logFileName = f'{y}{m}{d}_{LOG_FILE_NAME}'
    event = f"{now}|{logLevel}|{caller}::{msg}"


    ## Determine what should be printed to the screen
    if DEBUG_LOG_LEVEL >= level:
        print(event)
    
    ## Always Write to log
    f = open(f"{logFileName}.log", "a")
    f.write(f"{event} \n")
    f.close()

'''
 levelToString(): to transalte log level to string
 level = int LEVEL_* constant
''' 
def levelToString(level):
    strLevel = None
    if level == LEVEL_INFO: strLevel = "I"
    if level == LEVEL_WARNING: strLevel = "W"
    if level == LEVEL_ERROR: strLevel = "E"
    if level == LEVEL_DEBUG: strLevel = "D"
    if level == LEVEL_VERBOSE: strLevel = "V"

    if strLevel == None:raise Exception("MATTLOG: LOG LEVEL NOT FOUND.")
    
    return strLevel

'''
 i/e/w/d/v/(): Helper Methods for each log level
 msg = String message
''' 
def i(msg):
    writeLogMessage(LEVEL_INFO, msg)

def e(msg):
    writeLogMessage(LEVEL_ERROR, msg)

def w(msg):
    writeLogMessage(LEVEL_WARNING, msg)

def d(msg):
    writeLogMessage(LEVEL_DEBUG, msg)

def v(msg):
    writeLogMessage(LEVEL_VERBOSE, msg)

'''
 Run tests if script is directly executed.
'''  
if __name__ == "__main__":
    LOG_FILE_NAME = "TestLog"
    DEBUG_LOG_LEVEL = LEVEL_VERBOSE
    
    i("Testing Info")
    w("Testing Warn")
    e("Testing Err")
    d("Testing Debug")
    v("Testing Verbose")