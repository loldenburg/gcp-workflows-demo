import re
import time
from ftplib import FTP
from io import BytesIO, StringIO

from dateutil import parser


def to_expected_folder(folder):
    return '/' + folder if folder != '/' else '/'


def upload_to_ftp(buffer: StringIO or BytesIO,
                  file_name: str,
                  ftp_address: str,
                  ftp_user: str,
                  ftp_passwd: str,
                  ftp_folder: str = "/",
                  file_encoding: str = 'utf-8',
                  retries: int = 3,
                  retry_delay: int = 5, timeout: bool = None) -> str:
    """Sends supplied `buffer` to an FTP server as a file with the specified name.
    :returns: URL to the uploaded file    
    """
    currRetry = 0
    while currRetry < retries:
        try:
            print(f'Sending {file_name} file to the FTP server.')
            text = buffer.getvalue()
            bio = BytesIO(str.encode(text, file_encoding))
            ftp = FTP(ftp_address, timeout=timeout)
            ftp.login(user=ftp_user, passwd=ftp_passwd)
            expected_folder = to_expected_folder(ftp_folder)
            if ftp.pwd() != expected_folder:
                ftp.cwd(ftp_folder)
            ftp.storbinary('STOR ' + file_name, bio)
            ftp.quit()
            result = 'http://{}/{}'.format(ftp_address, file_name)
            print(f'File {file_name} is uploaded to the FTP server and is accessible at {result}.')
            return result
        except Exception as e:
            if "ftp" in locals():  # disconnect and reconnect
                ftp.quit()
            time.sleep(retry_delay)
            currRetry += 1
            print(f"Error uploading file to FTP: {e}. Trying again (attempt {currRetry} of {retries})")

    raise Exception(f"Could not upload {file_name} to FTP!")


def download_from_ftp(file_name: str,
                      ftp_address: str,
                      ftp_user: str,
                      ftp_passwd: str,
                      ftp_folder: str,
                      timeout: int = None) -> BytesIO or None:
    """Downloads the file denoted by the `file_name` from the FTP server and returns its content as BytesIO buffer.
    :return: binary content of the file or None if the file is not present
    """
    print(f'Getting {file_name} from the FTP server {ftp_address} in folder {ftp_folder}.')
    ftp = FTP(ftp_address, timeout=timeout)
    ftp.login(user=ftp_user, passwd=ftp_passwd)
    print('Connection with ftp was established')
    expected_folder = to_expected_folder(ftp_folder)
    if ftp.pwd() != expected_folder:
        ftp.cwd(ftp_folder)
    if file_name not in ftp.nlst():
        print("file not found! stopping execution!")
        return None
    print(f'file {file_name} exists. Starting download.')
    result = BytesIO()
    ftp.retrbinary('RETR ' + file_name, result.write)
    ftp.quit()
    print(f'File {file_name} is downloaded from the FTP server into an in-memory buffer.')
    return result


def delete_file(file_name: str,
                ftp_address: str,
                ftp_user: str,
                ftp_passwd: str,
                ftp_folder: str = '/') -> bool or None:
    """Deletes a file denoted by `file_name` from an FTP server if it exists. Otherwise returns None
    :rtype: Boolean or None
    """
    print(f'Deleting file {file_name} from {ftp_address} in folder {ftp_folder}')
    ftp = FTP(ftp_address)
    ftp.login(ftp_user, ftp_passwd)
    ftp.cwd(ftp_folder)
    if file_name not in ftp.nlst():
        print("file not found! stopping execution!")
        return None
    else:
        ftp.delete(file_name)
        print("file deleted!")
    print('Closing FTP connection')
    ftp.close()
    return True


def get_file_names(ftp_address, ftp_user, ftp_passwd, ftp_folder):
    """Returns a list of file names on an FTP
    :return: list of file names
    :rtype: list of str
    """
    print(f'Getting file names on {ftp_address} in folder {ftp_folder}')
    ftp = FTP(ftp_address)
    ftp.login(ftp_user, ftp_passwd)
    ftp.cwd(ftp_folder)
    files = ftp.nlst()
    return files


def list_files_on_ftp(file_name_re: str,
                      ftp_address: str,
                      ftp_user: str,
                      ftp_passwd: str,
                      ftp_folder='/') -> list:
    """Returns a list of files that match a regular expression string in `file_name_re` in a defined ftp_folder
    on an FTP server.
    """
    file_name_rs = re.compile(file_name_re)
    files = get_file_names(ftp_address, ftp_user, ftp_passwd, ftp_folder)
    output = [file for file in files if file_name_rs.match(file)]
    return output


def get_file_modification_date(file_name: str,
                               ftp_address: str,
                               ftp_user: str,
                               ftp_passwd: str,
                               ftp_folder: str = "/"):
    """Gets the file modification date from an FTP server. The server must support the MDTM command. """
    print(f'getting file modification date for {file_name} on the FTP server {ftp_address} in folder {ftp_folder}.')
    ftp = FTP(ftp_address)
    ftp.login(ftp_user, ftp_passwd)
    ftp.cwd(ftp_folder)
    timestamp = ftp.voidcmd(f"MDTM {file_name}")[4:].strip()
    return parser.parse(timestamp)
