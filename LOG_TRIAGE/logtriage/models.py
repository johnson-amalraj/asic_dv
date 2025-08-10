from dataclasses import dataclass

@dataclass
class LogRow:
    id: str
    testcase: str
    testopt: str
    type: str 
    count: int
    message: str
    orig_message: str
    logtype: str
    logfilepath: str
    linenumber: int

