import logging
import cv2
import numpy as np
import json
import os
import base64
import logging
import azure.functions as func


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        body = json.dumps(req.get_json())
    except ValueError:
        return func.HttpResponse(
             "Invalid body",
             status_code=400
        )
    
    if body:
        logging.info(body)
        result = compose_response(body)
        return func.HttpResponse(result, mimetype="application/json")
    else:
        return func.HttpResponse(
             "Invalid body",
             status_code=400
        )


def compose_response(json_data):
    values = json.loads(json_data)['values']
    
    # Prepare the Output before the loop
    results = {}
    results["values"] = []
    
    for value in values:
        output_record = transform_value(value)
        if output_record != None:
            results["values"].append(output_record)
    return json.dumps(results, ensure_ascii=False)

## Perform an operation on a record
def transform_value(value):
    try:
        recordId = value['recordId']
    except AssertionError  as error:
        return None

    # Validate the inputs
    try:         
        assert ('data' in value), "'data' field is required."
        data = value['data']        
        base64String = data["image"]["data"]
        base64Bytes = base64String.encode('utf-8')
        inputBytes = base64.b64decode(base64Bytes)
        jpg_as_np = np.frombuffer(inputBytes, dtype=np.uint8)
        originalImage = cv2.imdecode(jpg_as_np, flags=1)
        slices = []
        for line in data["layoutText"]["lines"]:
            slicedImage = originalImage[line["boundingBox"][0]["x"]:line["boundingBox"][0]["y"], line["boundingBox"][3]["x"]:line["boundingBox"][3]["y"]]
            if(slicedImage.size >0):
                is_success, im_buf_arr = cv2.imencode(".jpg", slicedImage)
                byte_im = im_buf_arr.tobytes()
                base64Bytes = base64.b64encode(byte_im)
                base64String = base64Bytes.decode('utf-8')
                aslice = { "$type": "file", 
                        "data": base64String 
                        }
                slices.append(aslice)


    except AssertionError  as error:
        return (
            {
            "recordId": recordId,
            "errors": [ { "message": "Error:" + error.args[0] }   ]       
            })

    

    return ({
            "recordId": recordId,
            "data": {
                "slices": slices
                    }
            })