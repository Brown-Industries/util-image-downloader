# Matrix Image Downloader

This is a python utility to download tooling images from a variety of sources to a speicifed directory. Images are only downloaded when:
- the item exists in Matrix
- an image does not exist in the target directory. 
 
This is accomplished by quering the Matrix database for items, comparing that list to what is already in the target directory and then removing any excluded items.

An excluded item is defined in the `excluded.txt` file and expects one item per line. Any items in this file will be skipped from the search. This is useful if an item is pulling the wrong image so that it is not looked up again.

## Usage

Tested and used with python 3.11. 

`pip install -r requirements.txt` to install needed modules.

`python main.py --help` : for genearl usage information


### Arguments
 `--imgdir`: Directory to save images

 `--matrix_pc`: The Matrix PC Address, for example MatrixPC\SQLEXPRESS

 `--matrix_db`: The name of the Matrix DB in MSSQL. ex. MSIMatrix

 `--user`: Username of database user 

 `--pwd`: Password of database user

### Outputs
The script will save all images to the specified imgdir. A `failed_items.txt` file will be generated in the script directory that contains a list of items that were not found.