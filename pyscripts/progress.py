


def uploadProgress(localpath, filename, sent, total):
    """Function to watch the progress of upload operation.

    :param localpath: path of the file.
    :param filename: name of the file.
    :param sent: number of bytes sent in upload.
    :param total: number of bytes of the file to upload.
    """
    percent = (sent * 100) / total
    print(
        f"\r{filename.decode()}: upload progress "
        f"{percent:.0f}%: {sent}/{total} (bytes)", 
        end='', 
        flush=True
    )


def downloadProgress(localpath, filename, downloaded, total):
    """Function to watch the progress of download operation.
    
    :param localpath: path of the file.
    :param filename: name of the file.
    :param downloaded: number of bytes sent in upload.
    :param total: number of bytes of the file to upload.
    """
    percent = (downloaded * 100) / total
    print(
        f"\r{filename.decode()}: download progress "
        f"{percent:.0f}%: {downloaded}/{total} (bytes)", 
        end='', 
        flush=True  
    )