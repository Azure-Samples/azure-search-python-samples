# Create Cognitive Search Index from CSV file

1. Change the following values in the `bulk_upload.py` file:

    * YOUR-SEARCH-RESOURCE-NAME (not the full URL)
    * YOUR-SEARCH-ADMIN-KEY

1. Install the requirements and run the script:

    ```bash
    pip install -r requirements.txt && \
    python bulk-upload.py
    ```

1. Script runs with results:

    ```bash
    Schema uploaded; Index created for good-books.
    Batch sent! - #1
    Batch sent! - #2
    Batch sent! - #3
    Batch sent! - #4
    Batch sent! - #5
    Batch sent! - #6
    Batch sent! - #7
    Batch sent! - #8
    Batch sent! - #9
    Batch sent! - #10
    Done!
    Upload complete

    Done. Press any key to close the terminal.
    ```

If you get a "file not found error" on good-books-index.json, try adding the "Terminal: Execute in File Directory" in Settings > Extensions > Python.