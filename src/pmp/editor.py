import os
import subprocess
import tempfile

from pmp.errors import PMPError


def edit_with_editor(initial_content=""):
    """
    Opens the user's preferred editor to edit content and returns the edited text.
    """
    editor = os.environ.get("EDITOR")
    if not editor:
        # Fallback for common editors on different platforms
        if os.name == "posix":  # Linux/macOS
            editor = "nano"
        elif os.name == "nt":  # Windows
            editor = "notepad.exe"
        else:
            raise RuntimeError(
                "No editor found. Please set the EDITOR environment variable."
            )

    with tempfile.NamedTemporaryFile(
        mode="w+", delete=False, encoding="utf-8"
    ) as tmp_file:
        tmp_file.write(initial_content)
        tmp_file_path = tmp_file.name

    try:
        subprocess.run([editor, tmp_file_path], check=True)
        with open(tmp_file_path, "r", encoding="utf-8") as f:
            edited_content = f.read()
        if not edited_content:
            raise PMPError("No content found. Please try again.")
        return edited_content
    except subprocess.CalledProcessError as e:
        raise PMPError(f"Error launching editor: {e}") from e
    finally:
        os.remove(tmp_file_path)  # Clean up the temporary file


if __name__ == "__main__":
    initial_text = "Enter your message here:\n"
    user_input = edit_with_editor(initial_text)

    if user_input is not None:
        print("\nUser input:")
        print(user_input)
