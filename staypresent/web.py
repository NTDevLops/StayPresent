_response = "StayPresent"

def text(message: str):
    global _response
    _response = str(message)

def json(data):
    global _response
    _response = data

def get():
    return _response