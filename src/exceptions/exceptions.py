class NaukriClientError(Exception):
    pass

class NaukriAuthError(NaukriClientError):

    def __init__(self, message='Authentication failed', status_code=None):
        msg = f'[AUTH ERROR] {message}'
        if status_code:
            msg += f' | HTTP {status_code}'
        super().__init__(msg)

class NaukriNetworkError(NaukriClientError):

    def __init__(self, message='Network request failed', url=None):
        msg = f'[NETWORK ERROR] {message}'
        if url:
            msg += f' | URL: {url}'
        super().__init__(msg)

class NaukriParseError(NaukriClientError):

    def __init__(self, message='Failed to parse response', response_snippet=None):
        msg = f'[PARSE ERROR] {message}'
        if response_snippet:
            msg += f' | Response: {response_snippet[:200]}'
        super().__init__(msg)

class NaukriUploadError(NaukriClientError):

    def __init__(self, message='Upload failed', filename=None):
        msg = f'[UPLOAD ERROR] {message}'
        if filename:
            msg += f' | File: {filename}'
        super().__init__(msg)
