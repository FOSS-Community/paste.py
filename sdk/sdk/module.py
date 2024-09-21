import requests
from typing import Optional, Union
from pathlib import Path

class PasteBinSDK:
    def __init__(self, base_url: str = "https://paste.fosscu.org"):
        self.base_url = base_url

    def create_paste(self, content: Union[str, Path], file_extension: str) -> str:
        """
        Create a new paste.
        :param content: The content to paste, either as a string or a Path to a file
        :param file_extension: File extension for syntax highlighting (required)
        :return: The unique identifier of the created paste
        """
        try:
            if isinstance(content, Path):
                with open(content, 'r', encoding='utf-8') as f:
                    content = f.read()

            data = {
                'content': content,
                'extension': file_extension
            }
            response = requests.post(f"{self.base_url}/api/paste", json=data)
            response.raise_for_status()
            result = response.json()
            return result['uuid']
        except requests.RequestException as e:
            raise RuntimeError(f"Error creating paste: {str(e)}")

    def get_paste(self, uuid: str) -> dict:
        """
        Retrieve a paste by its unique identifier.
        :param uuid: The unique identifier of the paste
        :return: A dictionary containing the paste details (uuid, content, extension)
        """
        try:
            response = requests.get(f"{self.base_url}/api/paste/{uuid}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Error retrieving paste: {str(e)}")

    def delete_paste(self, uuid: str) -> str:
        """
        Delete a paste by its unique identifier.
        :param uuid: The unique identifier of the paste
        :return: A confirmation message
        """
        try:
            response = requests.delete(f"{self.base_url}/paste/{uuid}")
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            raise RuntimeError(f"Error deleting paste: {str(e)}")

    def get_languages(self) -> dict:
        """
        Get the list of supported languages for syntax highlighting.
        :return: A dictionary of supported languages
        """
        try:
            response = requests.get(f"{self.base_url}/languages.json")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Error fetching languages: {str(e)}")