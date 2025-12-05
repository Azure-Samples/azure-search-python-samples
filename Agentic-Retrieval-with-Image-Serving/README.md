# Azure Search Image Serving Experiments

This project provides a tool to compare different Azure Search Knowledge Base configurations, specifically focusing on the effects of the `enable_image_serving` and `answer_synthesis` parameters on search results.

## Overview

The `image_serving_experiments.py` script runs systematic comparisons of Azure Search Knowledge Base responses with three different parameter combinations:

1. **answer_synthesis=False** (image serving not applicable)
2. **enable_image_serving=False, answer_synthesis=True** 
3. **enable_image_serving=True, answer_synthesis=True**

The script generates a detailed markdown report comparing the responses for each configuration.

## Files Description

- **`image_serving_experiments.py`** - Main script that runs the experiments and generates comparison reports
- **`search_client_utils.py`** - Utility module containing Azure Search client functionality
- **`requirements.txt`** - Python package dependencies
- **`.env.sample`** - Template for environment variables


## Prerequisites

1. **Azure Search Service** - You need an Azure Search service with a configured knowledge base
2. **Python 3.7+** - Required for running the scripts
3. **Azure Search API Key** - Admin key for your Azure Search service

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

1. Copy the sample environment file:
   ```bash
   copy .env.sample .env
   ```

2. Edit `.env` and add your Azure Search credentials:
   ```bash
   AZURE_SEARCH_ENDPOINT=https://your-search-service.search.windows.net
   # will use Azure Active Directory (AAD) authentication if API key is empty
   AZURE_SEARCH_API_KEY=your_admin_api_key_here
   ```

### 3. Configure Knowledge Base and Questions

Edit `image_serving_experiments.py` to customize:

1. **Knowledge Base Name**: Update the `kb_name` variable
   ```python
   kb_name = "your-kb-name"  # Replace with your actual KB name
   ```

2. **Test Questions**: Modify the `questions` list with your test queries
   ```python
   questions = [
       "Your first test question here",
       "Your second test question here",
       # Add more questions as needed
   ]
   ```

## Usage

### Running the Experiments

Execute the script from the command line:

```bash
python image_serving_experiments.py
```

### What Happens During Execution

1. **Initialization**: The script loads environment variables and connects to Azure Search
2. **Question Processing**: For each question in your list, it makes three API calls:
   - With `answer_synthesis=False`
   - With `answer_synthesis=True, enable_image_serving=False`
   - With `answer_synthesis=True, enable_image_serving=True`
3. **Report Generation**: Creates a timestamped markdown file with detailed results

### Output

The script generates a markdown report file named:
```
image_serving_experiments_YYYYMMDD_HHMMSS.md
```

