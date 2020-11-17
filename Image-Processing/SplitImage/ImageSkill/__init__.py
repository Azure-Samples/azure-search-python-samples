import logging
import cv2
import numpy as np
import json
import os
import base64
import logging
import azure.functions as func

def base64EncodeImage(image):
    is_success, im_buf_arr = cv2.imencode(".jpg", image)
    byte_im = im_buf_arr.tobytes()
    base64Bytes = base64.b64encode(byte_im)
    base64String = base64Bytes.decode('utf-8')
    return base64String

def obfuscate_data(image, factor=3.0):
    (h, w) = image.shape[:2]
    kW = int(w / factor)
    kH = int(h / factor)
    # ensure the width of the kernel is odd
    if kW % 2 == 0:
        kW -= 1
    # ensure the height of the kernel is odd
    if kH % 2 == 0:
        kH -= 1
    # apply a Gaussian blur to the input image using our computed
    # kernel size
    return cv2.GaussianBlur(image, (kW, kH), 0)

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
        for pii_entity in data["pii_entities"]:
            if(pii_entity["type"] == "Phone Number"):
                for line in data["layoutText"]["lines"]:
                    if(pii_entity["text"] in line["text"]):
                        startX = line["boundingBox"][0]["x"]
                        startY = line["boundingBox"][0]["y"]
                        endX = line["boundingBox"][2]["x"]
                        endY = line["boundingBox"][2]["y"]
                        slicedImage = originalImage[startY:endY, startX:endX]
                        if(slicedImage.size >0):
                            fuzzy = obfuscate_data(slicedImage)
                            originalImage[startY:endY, startX:endX] = fuzzy 
                            base64String = base64EncodeImage(slicedImage)   
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
                "slices": slices,
                "original": { "$type": "file", 
                        "data": base64EncodeImage(originalImage) 
                        }
                    }
            })