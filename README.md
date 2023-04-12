# Matrix Image Downloader

This is a python utility to download tooling images from a variety of sources to a speicifed directory. The script will query the Matrix database and only gather images for tools managed in Matrix.

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