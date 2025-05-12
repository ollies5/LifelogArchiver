import json
import time
import os
import sys # For sys.exit()

# Attempt to import dependencies and provide helpful messages if they are missing
try:
    import requests
except ImportError:
    print("Error: The 'requests' library is not installed. Please install all dependencies by running: pip install requests tzlocal tqdm")
    sys.exit(1)

try:
    import tzlocal
except ImportError:
    print("Error: The 'tzlocal' library is not installed. Please install all dependencies by running: pip install requests tzlocal tqdm")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    print("Error: The 'tqdm' library is not installed. Please install all dependencies by running: pip install requests tzlocal tqdm")
    sys.exit(1)

# --- Configuration ---
# API Key will be fetched from environment variable or user input
API_KEY = None
API_KEY_ENV_VAR = "LIMITLESS_API_KEY"

USER_AGENT = 'LifelogArchiver/1.0 (ollies5/LifelogArchiver)'

VERBOSE_LOGGING = False # Set to True for detailed request logs, URLs, and cursor info

BASE_URL = 'https://api.limitless.ai/v1/lifelogs'
OUTPUT_FILE = 'all_lifelogs.txt'

# --- User Desired Parameters & API Settings ---
REQUEST_LIMIT_PER_PAGE = 10
REQUEST_DELAY_SECONDS = 1
CURRENT_FETCH_DIRECTION = 'asc'
INCLUDE_MARKDOWN_PARAM = 'false' # User preference
INCLUDE_HEADINGS_PARAM = 'false' # User preference

# --- Retry Configuration for 5xx errors ---
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5
CLIENT_REQUEST_TIMEOUT = 30

# --- Helper Functions ---
def fetch_lifelogs_page(api_key_to_use, cursor=None, limit=REQUEST_LIMIT_PER_PAGE, direction=CURRENT_FETCH_DIRECTION):
    headers = {
        'X-API-Key': api_key_to_use,
        'User-Agent': USER_AGENT,
        'Content-Type': 'application/json'
    }
    try:
        local_timezone = str(tzlocal.get_localzone())
    except Exception as e:
        tqdm.write(f"Warning: Could not get local timezone: {e}. Defaulting to UTC.")
        local_timezone = "UTC"

    params = {
        'limit': limit,
        'direction': direction,
        'includeMarkdown': INCLUDE_MARKDOWN_PARAM,
        'includeHeadings': INCLUDE_HEADINGS_PARAM,
        'timezone': local_timezone
    }
    if cursor:
        params['cursor'] = cursor

    succeeded_after_retry = False
    for attempt in range(MAX_RETRIES):
        if VERBOSE_LOGGING:
            tqdm.write(f"Requesting URL: {BASE_URL} with params: {params} (Attempt {attempt + 1}/{MAX_RETRIES})")
        try:
            response = requests.get(BASE_URL, headers=headers, params=params, timeout=CLIENT_REQUEST_TIMEOUT)
            if succeeded_after_retry and response.ok:
                tqdm.write(f"Success after retry! (Attempt {attempt + 1}/{MAX_RETRIES}). Continuing fetch...")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            status_code = response.status_code
            error_type_message = f"API error ({status_code})"

            if status_code == 401: error_type_message = "Authentication error (401 - Unauthorized). Please check your API key."
            elif status_code == 403: error_type_message = "Permission error (403 - Forbidden)."
            elif status_code == 404: error_type_message = "API endpoint not found (404)."
            elif status_code == 429: error_type_message = "API error (429 - Too Many Requests / Rate Limited)."
            elif status_code == 500: error_type_message = "Server error (500 - Internal Server Error)."
            elif status_code == 502: error_type_message = "Server error (502 - Bad Gateway)."
            elif status_code == 503: error_type_message = "Server error (503 - Service Unavailable)."
            elif status_code == 504:
                error_type_message = ("Server error (504 - Gateway Timeout). "
                                      "Limitless is probably rate limiting you. ")
            elif 400 <= status_code < 500: error_type_message = f"Client error ({status_code}). Check request parameters."
            elif 500 <= status_code < 600: error_type_message = f"Server error ({status_code})."

            if (500 <= status_code < 600 or status_code == 429) and attempt < MAX_RETRIES - 1:
                tqdm.write(f"{error_type_message} Retrying in {RETRY_DELAY_SECONDS}s... (Retry {attempt + 1} of {MAX_RETRIES -1})")
                succeeded_after_retry = True
                time.sleep(RETRY_DELAY_SECONDS)
                continue
            else:
                tqdm.write(f"{error_type_message} Giving up on this page after {attempt + 1} attempt(s).")
                if VERBOSE_LOGGING:
                    tqdm.write(f"Failed URL: {response.url}")
                    tqdm.write(f"Response content (first 500 chars): {response.content.decode(errors='ignore')[:500]}")
                return None
        except requests.exceptions.RequestException as req_err:
            error_message = f"Request network/timeout error: {req_err}"
            if attempt < MAX_RETRIES - 1:
                tqdm.write(f"{error_message}. Retrying in {RETRY_DELAY_SECONDS}s... (Retry {attempt + 1} of {MAX_RETRIES-1})")
                succeeded_after_retry = True
                time.sleep(RETRY_DELAY_SECONDS)
                continue
            else:
                tqdm.write(f"{error_message}. Max retries reached. Giving up on this page.")
                return None
        except json.JSONDecodeError as json_err:
            tqdm.write(f"Failed to decode JSON response from API: {json_err}")
            if VERBOSE_LOGGING and 'response' in locals():
                 tqdm.write(f"Raw response text (first 500 chars): {response.text[:500]}...")
            return None
    return None

def main():
    global API_KEY # Allow main to set the global API_KEY

    # Get API Key
    api_key_from_env = os.getenv(API_KEY_ENV_VAR)
    if api_key_from_env:
        print(f"Using Limitless API key from environment variable '{API_KEY_ENV_VAR}'.")
        API_KEY = api_key_from_env
    else:
        print(f"Didn't find an API key in the environment variable '{API_KEY_ENV_VAR}' You can set this if you want to run this script regularly, or, just input it below.")
        try:
            api_key_input = input("Please enter your Limitless API key: ").strip()
            if not api_key_input:
                print("No API key provided. Exiting.")
                sys.exit(1)
            API_KEY = api_key_input
        except KeyboardInterrupt:
            print("\nAPI key input cancelled by user. Exiting.")
            sys.exit(1)

    current_cursor = None
    page_count = 0
    
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            pass 
        print(f"\nOutput file '{OUTPUT_FILE}' initialized/cleared for the new run.")
    except IOError as e:
        print(f"CRITICAL ERROR: Could not initialize/clear output file '{OUTPUT_FILE}': {e}")
        print("Please check file permissions and path. Exiting.")
        sys.exit(1)

    print(f"Starting lifelog fetch: limit_per_page={REQUEST_LIMIT_PER_PAGE}, direction='{CURRENT_FETCH_DIRECTION}', markdown={INCLUDE_MARKDOWN_PARAM}, headings={INCLUDE_HEADINGS_PARAM}")
    print(f"Logs will be written incrementally to: {OUTPUT_FILE}\n")

    with tqdm(total=None, unit=" lifelogs", desc="Fetched", dynamic_ncols=True, bar_format='{l_bar}{bar}| {n_fmt}{unit} [{elapsed}<{remaining}, {rate_fmt}{postfix}]') as pbar:
        while True:
            page_count += 1
            if VERBOSE_LOGGING:
                log_message = f"Fetching page {page_count}"
                if current_cursor and page_count > 1:
                    log_message += f" with cursor: {current_cursor[:20]}..." 
                tqdm.write(log_message)

            data_payload = fetch_lifelogs_page(API_KEY, # Use the globally set API_KEY
                                               cursor=current_cursor,
                                               limit=REQUEST_LIMIT_PER_PAGE,
                                               direction=CURRENT_FETCH_DIRECTION)

            if not data_payload:
                tqdm.write("\nFailed to fetch data for a page after all retries. Check logs above. Stopping.")
                break
            
            lifelogs_on_page = data_payload.get('data', {}).get('lifelogs', [])
            
            if lifelogs_on_page:
                try:
                    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
                        for log_entry in lifelogs_on_page:
                            f.write(json.dumps(log_entry) + '\n')
                    if VERBOSE_LOGGING:
                        tqdm.write(f"Appended {len(lifelogs_on_page)} logs to {OUTPUT_FILE}")
                except IOError as e:
                    tqdm.write(f"\nERROR writing to file {OUTPUT_FILE}: {e}. Further writing may fail. Stopping.")
                    break 

                pbar.update(len(lifelogs_on_page))
            
            if not lifelogs_on_page and page_count > 1 : 
                pbar.refresh() 
                tqdm.write("\nNo more lifelogs found on this page (API returned empty list).")
                if VERBOSE_LOGGING:
                    tqdm.write(f"DEBUG: Full API response on empty page: {json.dumps(data_payload, indent=2)}")
                break
            elif not lifelogs_on_page and page_count == 1: 
                pbar.refresh()
                tqdm.write("\nNo lifelogs found on the very first page.")
                if VERBOSE_LOGGING:
                    tqdm.write(f"DEBUG: Full API response on empty first page: {json.dumps(data_payload, indent=2)}")
                break

            meta_info = data_payload.get("meta", {})
            lifelogs_meta = meta_info.get("lifelogs", {})
            next_cursor = lifelogs_meta.get("nextCursor")

            if not next_cursor:
                pbar.refresh()
                tqdm.write("\nNo 'nextCursor' found in API response (meta.lifelogs.nextCursor).")
                if VERBOSE_LOGGING:
                    tqdm.write(f"DEBUG: Full API response when no 'meta.lifelogs.nextCursor' found: {json.dumps(data_payload, indent=2)}")
                
                if len(lifelogs_on_page) < REQUEST_LIMIT_PER_PAGE and lifelogs_on_page : 
                    tqdm.write("Number of items fetched is less than the limit, confirming this was the last page.")
                elif lifelogs_on_page: 
                     tqdm.write("Number of items fetched matches the limit, but no cursor found. Assuming end of data.")
                break
            
            if VERBOSE_LOGGING:
                tqdm.write(f"Next cursor found: {next_cursor[:20]}...")
            current_cursor = next_cursor
            
            if len(lifelogs_on_page) < REQUEST_LIMIT_PER_PAGE: # If API returns less than asked, it's the end.
                pbar.refresh()
                tqdm.write("\nFetched fewer lifelogs than requested batch size; assuming this was the last page.")
                break

            if page_count > 0 and REQUEST_DELAY_SECONDS > 0 : # Don't sleep before the first page
                 time.sleep(REQUEST_DELAY_SECONDS)

    final_fetched_count = pbar.n if pbar else 0 
    print(f"\n\nFetching process complete. Total lifelogs fetched and processed: {final_fetched_count}")
    if final_fetched_count > 0:
        print(f"Data has been incrementally written to '{OUTPUT_FILE}'.")
    else:
        print(f"No lifelogs were fetched. '{OUTPUT_FILE}' should be empty or reflect a previous run if initialization failed.")
    
    print("--- SCRIPT COMPLETE ---")

if __name__ == '__main__':
    main()