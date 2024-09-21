import requests
from typing import Optional, Union
from pathlib import Path

class PasteBinSDK:
    def __init__(self, base_url: str = "http://paste.fosscu.org"):
        self.base_url = base_url

    def create_paste(self, content: Union[str, Path], file_extension: Optional[str] = None) -> str:
        """
        Create a new paste.
        
        :param content: The content to paste, either as a string or a Path to a file
        :param file_extension: Optional file extension for syntax highlighting
        :return: The unique identifier of the created paste
        """
        if isinstance(content, Path):
            with open(content, 'rb') as f:
                files = {'file': f}
                response = requests.post(f"{self.base_url}/file", files=files)
        else:
            data = {'content': content}
            if file_extension:
                data['extension'] = file_extension
            response = requests.post(f"{self.base_url}/web", data=data)
        
        response.raise_for_status()
        return response.text.strip()

    def get_paste(self, uuid: str) -> str:
        """
        Retrieve a paste by its unique identifier.
        
        :param uuid: The unique identifier of the paste
        :return: The content of the paste
        """
        response = requests.get(f"{self.base_url}/paste/{uuid}")
        response.raise_for_status()
        return response.text

    def delete_paste(self, uuid: str) -> str:
        """
        Delete a paste by its unique identifier.
        
        :param uuid: The unique identifier of the paste
        :return: A confirmation message
        """
        response = requests.delete(f"{self.base_url}/paste/{uuid}")
        response.raise_for_status()
        return response.text
