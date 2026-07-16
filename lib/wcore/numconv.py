def number(string: str):
    if int(string) != float(string):
        return float(string)
    else:
        if len(str(int(string))) != len(string):
            return float(string)
    
    return int(string)