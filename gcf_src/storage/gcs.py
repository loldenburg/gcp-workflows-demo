import mimetypes
from io import StringIO, BytesIO

from google.cloud import storage

from gcf_src.config import cfg

storage_client = storage.Client()
# Name of the default project GCS bucket
DEFAULT_BUCKET = cfg.GCS_DEFAULT_BUCKET


def download_file(file_name, bucket_name=DEFAULT_BUCKET, file_encoding='utf-8', encode=False):
    """Downloads a file from the bucket.

    If `encode` is `True` the file content is decoded using specified encoding, otherwise the content
    of the file is returned as `BytesIO`.

    If the file is not present in the GCS `None` is returned.

    :param file_name: name of the file within the bucket
    :type file_name: str
    :param bucket_name: name of the GCS bucket
    :type bucket_name: str
    :param file_encoding: file encoding
    :type file_encoding: str
    :param encode: defines whether the file should be decoded
    :type encode: bool
    :return: file content
    :rtype: StringIO or BytesIO or None
    """
    print(f'Downloading file {file_name} from GCS bucket {bucket_name}')
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.get_blob(blob_name=file_name)
    if blob is None:
        print(f'File {file_name} is not found.')
        return None
    byte_arr = blob.download_as_string()
    if encode:
        print(f'Decoding file {file_name} using {file_encoding} encoding.')
        encoded_str = byte_arr.decode(encoding=file_encoding)
        return StringIO(encoded_str)
    return BytesIO(byte_arr)


def upload_file(dest_file_name: str = None, data: object = None, content_type: str = None,
                bucket_name: str = DEFAULT_BUCKET,
                file_encoding: str = 'utf-8', encode: bool = True, no_cache: bool = False,
                metadata: dict = None, retries: int = None, timeout: int = None) -> str:
    """Uploads supplied data to the bucket with a specific destination file name.

    :param timeout: timeout in seconds for uploads (defaults to GCS default of 60 seconds)
    :param retries: retries if upload fails (defaults to no retries)
    :param dest_file_name: name of the file in the bucket.
    :param data: the data to store in the file (bytes or str or StringIO or BytesIO)
    :param content_type: type of the content being uploaded. If None, the type is inferred from the file name.
    :param bucket_name: name of the bucket into which the content with the specified name  being uploaded.
    :param file_encoding: encoding to use
    :param encode: encode the stringIO (True) or is it already encoded?
    :param no_cache: set to True if you want to disable caching of the uploaded file
    :param metadata: GCS metadata to be stored with the file
    :return: URL of the stored file
    """
    print(f'Uploading file {dest_file_name} of type {content_type} to GCS bucket {bucket_name}.')
    if content_type is None:
        guessed_type, _ = mimetypes.guess_type(dest_file_name)
        content_type = guessed_type or 'application/octet-stream'
        print(f'Inferred Content Type {content_type} from file name.')
    unpacked_data = data
    if isinstance(data, StringIO) or isinstance(data, BytesIO):
        print('Unpacking data from StringIO/BytesIO.')
        data.seek(0)
        unpacked_data = data.read()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(dest_file_name)
    if isinstance(unpacked_data, str) and encode is True:
        print(f'Encoding string data as {file_encoding} bytes.')
        unpacked_data = unpacked_data.encode(file_encoding)
    blob.upload_from_string(unpacked_data, content_type, num_retries=retries, timeout=timeout)

    if no_cache is True:
        blob.cache_control = "no-cache, max-age=0"
        blob.patch()
        print(f"Set the blob to not use caching.")
    if metadata is not None:
        # allows to set metadata on the blob
        blob.metadata = metadata
        blob.patch()
        print(f"Set the following metadata on the file: {metadata}")
    else:  # private
        print(f'File {blob.name} uploaded successfully and privately to {blob.self_link}, size: {blob.size}')
        return blob.self_link


def delete_file(bucket_name: str = DEFAULT_BUCKET, file_name: str = None):
    """Deletes a file from GCS."""

    print(
        f"File {file_name} in bucket {bucket_name} will be deleted.")
    source_bucket = storage_client.bucket(bucket_name)
    source_blob = source_bucket.blob(file_name)
    # Delete the file in the source bucket
    return source_blob.delete()
