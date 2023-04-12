import pyodbc
import os
import requests
import json
import argparse

import urllib.request
import urllib.parse

from tqdm import tqdm
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

parser = argparse.ArgumentParser(description="Download tool images for items in the Matrix database using MSMNI, specific vendors, and MSC as data sources")
parser.add_argument('--imgdir', default="./images", help='Directory to save images.')
parser.add_argument('--matrix_pc', required=True, help='Matrix PC address. ex. MatrixPC\SQLEXPRESS.')
parser.add_argument('--matrix_db', default="MSIMatrix", help='Matrix Database. ex. MSIMatrix.')
parser.add_argument('--user', required=True, help='User ID for the database connection.')
parser.add_argument('--pwd', required=True, help='Password for the database connection.')

args = parser.parse_args()

# 1. Connect to local MSSQL database and get a list of items
connection_string = f"Driver={{SQL Server}};Server={args.matrix_pc};Database={args.matrix_db};UID={args.user};PWD={args.pwd}"
conn = pyodbc.connect(connection_string)
cursor = conn.cursor()

#query = "SELECT TOP (100) [ITEM_CODE] as 'item_number' FROM [MSIMatrix].[dbo].[msi_Item_Master]"
query = "SELECT sim.item_number,sim.item_description,CASE WHEN im.item_code IS NULL THEN 'N' ELSE 'Y' END AS 'inMatrix' FROM   msi_staging_item_master sim LEFT JOIN ent_item_master im ON im.item_code = sim.item_number WHERE im.item_code IS NOT NULL"
cursor.execute(query)
db_items = [row.item_number for row in cursor.fetchall()]

# 2. Read a list of files from a directory
directory = args.imgdir
file_list = os.listdir(directory)

def load_excluded_items(file_path):
    excluded_items = set()
    with open(file_path, "r") as f:
        for line in f:
            excluded_item = line.strip()
            if excluded_item:
                excluded_items.add(excluded_item)
    return excluded_items

# 3. Compare the list from the database with the list from the directory and remove duplicates
file_list_without_extensions = [os.path.splitext(file)[0] for file in file_list]
unique_items = set(db_items) - set(file_list_without_extensions)

# Load excluded items from the excluded.txt file and remove them from unique_items
excluded_items = load_excluded_items("excluded.txt")
unique_items = unique_items - excluded_items

failed_items = []  # List to store failed items

def save_image(item_number, image_url):
    image_path = os.path.join(directory, f"{item_number}.jpg")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
        req = urllib.request.Request(image_url, headers=headers)
        response = urllib.request.urlopen(req)
        with open(image_path, "wb") as f:
            f.write(response.read())
        #print(f"Downloaded image for item: {item_number}")
        return True
    except Exception as e:
        #print(f"Failed to download image for item {item_number}: {e}")
        return False

def search_MSC(brand, mpn):
    # Note: MSC Download is not perfect. This is a quick and dirty download using their autocomplete search results.
    # Unfortunately it seems MSC has implemented some bot protections and time hasn't been spent to bypass and do more
    # proper crawling. However, it does work as a last ditch effort to get an image.

    headers = {"brUid": "uid=4797467037409:v=12.0:ts=1653171470053:hc=1006"}
    url = f"https://www.mscdirect.com/search/suggestions/beta?searchterm={mpn}"

    response = requests.get(url, headers=headers)
    
    data = json.loads(response.text)

    # Check if "searchSuggestion" array exists and "alternatePartNumber" matches ITEM_NUMBER
    search_suggestions = data.get("searchSuggestion", [])
    for suggestion in search_suggestions:
        alternate_part_number = suggestion.get("alternatePartNumber", None)
        
        if alternate_part_number is None:
            continue

        if alternate_part_number == mpn or (mpn in alternate_part_number and brand in alternate_part_number):
            # Download the image using "largeImageLink"
            image_info = suggestion.get("imageInfo", {})
            large_image_link = image_info.get("largeImageLink", "")

            if large_image_link:
                image_url = f"https://cdn.mscdirect.com/global/images/ProductImages/{large_image_link}"
                return save_image(brand + " " + mpn, image_url)
            break
    else:
        return False

def search_YG1(brand, mpn):
    url = f"https://www.yg1usa.com/feature/itemdetail.asp?edpno={mpn}"

    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    path = soup.find("td", {"class": "item_pic"}).find("img")["src"]
    
    if "noimage" in path:
        return False
    
    image_url = f"https://www.yg1usa.com{path}"
    return save_image(brand + " " + mpn, image_url)

def search_MIT(brand, mpn):
    # First we are going to use google to find the product page, because the MIT website sucks.
    query = f"site:mitsubishicarbide.net/mmus/ EDP {mpn}"
    # send search query and retrieve HTML content of search results page
    url = f"https://www.google.com/search?q={query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    # extract first search result URL from search results page
    search_result = soup.find("div", {"class": "g"})
    link = ""
    try:
        link = search_result.find("a")["href"]
    except Exception as e:
        # If no google results are found move on.
        return False
    
    # retrieve HTML content of first search result page
    response = requests.get(link, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    # extract EDP and image source from first search result page
    edp = soup.find("span", {"class": "edp"}).text.split(':')[1].strip()
    image_url = soup.find("div", {"class": "columnProImg"}).find("img")["src"]

    if not edp == mpn:
        return False

    return save_image(brand + " " + mpn, f"https://www.mitsubishicarbide.net{image_url}")

def search_HEL(brand, mpn):
    url = f"https://www.helicaltool.com/products/tool-details-{mpn}"

    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    image_url = soup.find("div", {"class": "main-image-wrapper"}).find("img")["src"]
    
    return save_image(brand + " " + mpn, image_url)

def process_item(item_number):
    brand = item_number[:3] # The first 3 characters
    mpn = item_number[4:]   # All but the first 4 characters

    image_url = f"https://zuwzc.brnind.com/{urllib.parse.quote(item_number)}.jpg"
    foundImage = save_image(item_number, image_url)
    if foundImage:
        return
   
    if brand == "ISC":
        image_url = f"http://www.iscar.com/SM/getCatalogImage.aspx?Cat={mpn}&Comp=IS"
        foundImage = save_image(item_number, image_url)
    elif brand == "TUN":
        image_url = f"http://www.iscar.com/SM/getCatalogImage.aspx?Cat={mpn}&Comp=TL"
        foundImage = save_image(item_number, image_url)
    elif brand == "GUH":
        guh_family = mpn.split("-")[0]
        image_url = f"https://www.guhring.com/App/GuhringUSA_files/ToolImages/{guh_family}.jpg"
        foundImage = save_image(item_number, image_url)
    elif brand == "YG1":
        foundImage = search_YG1(brand, mpn)
    elif brand == "MIT":
        foundImage = search_MIT(brand, mpn)
    elif brand == "HEL":
        foundImage = search_HEL(brand, mpn)

    if foundImage:
        return

    foundImage = search_MSC(brand, mpn)
    
    if not foundImage: 
        failed_items.append(item_number)
        
# Run multiple threads of our primary processing to speed things up.
num_threads = 10  # Set the number of threads based on your requirements
with ThreadPoolExecutor(max_workers=num_threads) as executor:
    results = list(tqdm(executor.map(process_item, unique_items), total=len(unique_items)))

# Write the failed items to a file
with open("failed_items.txt", "w") as f:
    for failed_item in failed_items:
        f.write(f"{failed_item}\n")
