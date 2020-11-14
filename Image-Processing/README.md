# Image Processing Sample

Cognitive Search can enrich images with text or images with other images. This sample demonstrates how to pass images to a custom skill and return images from the  custom skill back to the skillset.

## Redacting PII information from images

This sample deploys a skill to obfuscate or redact phone numbers from images. The skillset contains three skills:
1. OCR 
2. PII detection
3. Custom Skill to redact PII

The skillset OCR's the images and runs the extracted text through the PII detection skill to identify PII information. The custom skill then takes the image, layout text from  OCR and the identified PII information to obfuscate the image. The image with the PII infomration obfuscted is then returned to the skillset and projected to the knwoledge store.

## Confingure the components

This sample contains a Azure function and a Jupyter Python3 .ipynb file. Start by deploying the Azure function and saving the URL and code. 

The folder also contains a sample image with a phone number. Save this image to a container in a storage account. This container will be your data source for the enrichment pipeline.

Open the norebook in this folder and set the URL and other required variables in the first cell of the notebook, execute the cells of the notebook to configure and run the solution.

## Validation
Once the indexer completes, you will see a container `obfuscated` in the knowledge store with the phone number redacted. For comparision the original images are stored in a container `images`.
