# basic import
from mcp.server.fastmcp import FastMCP, Image
from mcp.server.fastmcp.prompts import base
from mcp.types import TextContent
from mcp import types
from apple_prompt import get_create_keynote_prompt, get_save_keynote_prompt
import subprocess
import time
import os
import threading
import sys
import tempfile

# instantiate an MCP server client
mcp = FastMCP("KeynoteAssistant")

# DEFINE TOOLS


@mcp.tool()
def create_keynote_with_text(
    text: str = "Apple", width: int = 540, height: int = 430
) -> dict:
    """
    Create a new Keynote presentation with a rectangular shape containing text.
    Rectangle specs are customizable with default 540x430, black text.
    """
    # Path for saving
    user_home = os.path.expanduser("~")
    file_path = f"{user_home}/Desktop/my_new.key"

    # Remove existing file if it exists
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"Removed existing file: {file_path}")
        except Exception as e:
            print(f"Error removing existing file: {str(e)}")
            return {
                "content": [
                    TextContent(
                        type="text", text=f"Error removing existing file: {str(e)}"
                    )
                ]
            }

    # Script to create a new Keynote presentation with rectangle and text
    # create_script = f"""
    # tell application "Keynote"
    # -- Open Keynote and create a new presentation
    # activate
    # delay 2
    #
    # -- Create a new presentation
    # make new document
    # delay 2
    #
    # -- Get a reference to the first slide
    # tell front document
    # tell the current slide
    # -- Create a new shape (rectangle)
    # set newShape to make new shape
    #
    # -- Set shape properties
    # set the width of newShape to {width}
    # set the height of newShape to {height}
    #
    # -- Center the shape on the slide
    # set the position of newShape to {{400, 300}}
    #
    # -- Add text to the shape
    # set the object text of newShape to "{text}"
    #
    # -- Format the text
    # tell the object text of newShape
    # set the font to "Helvetica"
    # set the size to 72
    # set the alignment to center
    # end tell
    # end tell
    #
    # -- Save the presentation
    # save in "{file_path}" replacing yes
    # delay 2
    #
    # -- Close Keynote
    # quit
    # end tell
    # end tell
    # """
    # Run the AppleScript to create the presentation
    create_script = get_create_keynote_prompt(text=text, width=width, height=height)
    try:
        # Create a temporary AppleScript file

        with tempfile.NamedTemporaryFile(
            suffix=".scpt", delete=False, mode="w"
        ) as script_file:
            script_file.write(create_script)
            script_path = script_file.name

        print(f"Created temporary script file: {script_path}")

        # Execute the AppleScript file
        create_result = subprocess.run(
            ["osascript", script_path], capture_output=True, text=True
        )

        # Clean up the temporary file
        os.remove(script_path)

    except:
        print(f"Error creating presentation: {create_result.stderr}")
        # return {
        # "content": [
        # TextContent(
        # type="text", text=f"Error creating presentation: {create_result.stderr}"
        # )
        # ]
        # }
        # if create_result.returncode != 0:
        # print(f"Error creating presentation: {create_result.stderr}")
        # return {
        # "content": [
        # TextContent(
        # type="text",
        # text=f"Error creating presentation: {create_result.stderr}",
        # )
        # ]
        # }

    # Run the AppleScript to save the file
    save_script = get_save_keynote_prompt()
    try:

        with tempfile.NamedTemporaryFile(
            suffix=".scpt", delete=False, mode="w"
        ) as script_file:
            script_file.write(save_script)
            script_path = script_file.name

        print(f"Created temporary script file: {script_path}")

        # Execute the AppleScript file
        create_result = subprocess.run(
            ["osascript", script_path], capture_output=True, text=True
        )

        # Clean up the temporary file
        os.remove(script_path)
    except:
        print(f"Error saving presentation: {create_result.stderr}")
        return {
            "content": [
                TextContent(
                    type="text",
                    text=f"Error saving presentation: {create_result.stderr}",
                )
            ]
        }

        return {
            "content": [
                TextContent(
                    type="text",
                    text=f"Keynote presentation with '{text}' created and saved to {file_path}",
                )
            ]
        }


# DEFINE PROMPTS
if __name__ == "__main__":
    # Check if running with mcp dev command
    print("STARTING KEYNOTE MCP SERVER")
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        mcp.run()  # Run without transport for dev server
    else:
        mcp.run(transport="stdio")  # Run with stdio for direct execution
