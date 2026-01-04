import json
def write_json(path, data):
    with open(path,"w") as f:
        json.dump(data,f,indent=2)
