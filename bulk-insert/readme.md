# Python bulk-insert: Create Azure AI Search Index from CSV file

This folder contains source code for a bulk-insert program that creates and loads an index using the good-books sample data in a CSV folder. It's the Python version of the `bulk-insert` content used in the [C# sample Add search to websites](https://learn.microsoft.com/azure/search/tutorial-csharp-overview). If you're a Python developer, you can subtitute this code to create a Python version of the sample app.

You can also run this code standalone to create a good-books index on your search service.

1. Check your search service to make sure you have room for an extra index. The Usage tab in the Azure portal's search service page provides this information. The maximum limit on the free tier is 3 indexes. The maximum limit on the basic tier is 15 indexes.

1. Change the following values in the `bulk-insert.py` file:

    * YOUR-SEARCH-RESOURCE-NAME (not the full URL)
    * YOUR-SEARCH-ADMIN-KEY

1. Create a virtual environment. Press Ctrl-Shift-P to open the command palette and search for `Python: Create Environment`.

1. Open an integrated terminal in Visual Studio Code.

1. Make sure the path is "azure-search-static-web-app/python/bulk-insert".

1. Install the dependencies:

    ```bash
    pip install -r requirements.txt
    ```

1. Run the program:

    ```bash
    py bulk-insert.py
    ```

1. You should see the following output:

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
    ```

If you get a "file not found error" on good-books-index.json, try adding the "Terminal: Execute in File Directory" in Settings > Extensions > Python.