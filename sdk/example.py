from sdk.module import PasteBinSDK


def test_pastebin_sdk():
    sdk = PasteBinSDK()

    try:
        # Create a paste
        paste_id = sdk.create_paste("print('Hello, World!')", ".py")
        print(f"Created paste with ID: {paste_id}")

        # Retrieve the paste
        content = sdk.get_paste(paste_id)
        print(f"Retrieved paste content: {content}")

        # Delete the paste
        result = sdk.delete_paste(paste_id)
        print(f"Delete result: {result}")

        # Get supported languages
        languages = sdk.get_languages()
        print(f"Number of supported languages: {len(languages)}")

    except RuntimeError as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    test_pastebin_sdk()
