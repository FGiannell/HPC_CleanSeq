
ALLOWED_EXTENSIONS = {'tsv'}


def allowedFile(filename: str) -> bool:
    """ Function to check if the file extension is allowed.
    
    :param filename: The filename with the file extension to check.
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def fileExtension(filename: str) -> str:
    """Function to get the extension of the uploaded file.

    :param filename: The filename with the file extension to get.
    """
    ext = filename.rsplit('.', 1)[1].lower()
    
    if ext == 'gz':
        pre = filename.rsplit('.', 1)[0].rsplit('.', 1)[1]
        ext = pre + '.' + ext
    
    return ext