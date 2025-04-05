import os
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
import asyncio
from google import genai
from concurrent.futures import TimeoutError
from functools import partial

# Load environment variables from .env file
load_dotenv()

# Access your API key and initialize Gemini client correctly
api_key = os.getenv("GOOGLE_API_KEY")  # Changed to GOOGLE_API_KEY to match your .env
if not api_key:
    print("ERROR: GOOGLE_API_KEY environment variable is not set!")
    print(
        "Please create a .env file with your GOOGLE_API_KEY or set it in your environment."
    )
    exit(1)

# Initialize the client with the API key
try:
    client = genai.Client(api_key=api_key)
    print("Successfully initialized Gemini client")
except Exception as e:
    print(f"Failed to initialize Gemini client: {e}")
    exit(1)

max_iterations = 1  # Only need 1 iteration: create and edit
last_response = None
iteration = 0
iteration_response = []
keynote_file_path = None  # Store the path to the created Keynote file


async def generate_with_timeout(
    client, prompt, timeout=2000
):  # Increased timeout for complex tasks
    """Generate content with a timeout"""
    print("Starting LLM generation...")
    try:
        # Convert the synchronous generate_content call to run in a thread
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: client.models.generate_content(
                    model="gemini-2.0-flash", contents=prompt
                ),
            ),
            timeout=timeout,
        )
        print("LLM generation completed")
        return response
    except TimeoutError:
        print("LLM generation timed out!")
        raise
    except Exception as e:
        print(f"Error in LLM generation: {e}")
        raise


def reset_state():
    """Reset all global variables to their initial state"""
    global last_response, iteration, iteration_response, keynote_file_path
    last_response = None
    iteration = 0
    iteration_response = []
    keynote_file_path = None


async def main():
    reset_state()  # Reset at the start of main
    print("Starting main execution...")
    try:
        # Create a single MCP server connection
        print("Establishing connection to MCP server...")
        server_params = StdioServerParameters(
            command="python", args=["mcp_server.py"]
        )  # Changed to mcp_server.py

        async with stdio_client(server_params) as (read, write):
            print("Step:1 - Connection established, creating session...")
            async with ClientSession(read, write) as session:
                print("Step:2 - Session created, initializing...")
                await session.initialize()

                # Get available tools
                print("Requesting tool list...")
                tools_result = await session.list_tools()
                tools = tools_result.tools
                print(f"Step:3 - Successfully retrieved {len(tools)} tools")

                # Create system prompt with available tools
                print("Step:4 - Creating system prompt...")
                print(f"Number of tools: {len(tools)}")

                try:
                    tools_description = []
                    for i, tool in enumerate(tools):
                        try:
                            # Get tool properties
                            params = tool.inputSchema
                            desc = getattr(
                                tool, "description", "No description available"
                            )
                            name = getattr(tool, "name", f"tool_{i}")

                            # Format the input schema in a more readable way
                            if "properties" in params:
                                param_details = []
                                for param_name, param_info in params[
                                    "properties"
                                ].items():
                                    param_type = param_info.get("type", "unknown")
                                    param_details.append(f"{param_name}: {param_type}")
                                params_str = ", ".join(param_details)
                            else:
                                params_str = "no parameters"

                            tool_desc = f"{i+1}. {name}({params_str}) - {desc}"
                            tools_description.append(tool_desc)
                            print(f"Added description for tool: {tool_desc}")
                        except Exception as e:
                            print(f"Error processing tool {i}: {e}")
                            tools_description.append(f"{i+1}. Error processing tool")

                    tools_description = "\n".join(tools_description)
                    print("Successfully created tools description")
                except Exception as e:
                    print(f"Error creating tools description: {e}")
                    tools_description = "Error loading tools"

                print("Step:5 - Tool Description Created")
                print("Created system prompt...")

                # Update examples to match your current available tools
                system_prompt = f"""You are a Keynote presentation assistant. You help create and edit Keynote presentations.

Available tools:
{tools_description}

You must respond with EXACTLY ONE line in one of these formats (no additional text):
1. For function calls:
   FUNCTION_CALL: function_name|param1|param2|...
   
2. For final answers:
   FINAL_ANSWER: [Your message here]

Important:
- In iteration 1: Create a new Keynote presentation with a title, content and save it to the desktop
- Only give FINAL_ANSWER when you have completed all necessary operations

Examples:
- FUNCTION_CALL: create_keynote_with_text|Hello World|540|430
- FINAL_ANSWER: [Presentation created and edited successfully]

DO NOT include any explanations or additional text.
Your entire response should be a single line starting with either FUNCTION_CALL: or FINAL_ANSWER:"""

                # Define the presentation topic and edit content
                presentation_topic = "Artificial Intelligence"
                edit_content = "Add a slide about Machine Learning applications"

                # Initial query for creating a presentation
                query = f"Create a Keynote presentation about {presentation_topic}"

                # Use global iteration variables
                global iteration, last_response, keynote_file_path

                while iteration < max_iterations:
                    print(f"\n--- Iteration {iteration + 1} ---")

                    if iteration == 0:
                        # First iteration: Create a presentation
                        current_query = query
                    elif iteration == 1:
                        # Second iteration: Edit the presentation
                        current_query = f"Now edit the presentation with this content: {edit_content}"

                    # Add previous responses to the context
                    if iteration_response:
                        current_query = (
                            current_query + "\n\n" + " ".join(iteration_response)
                        )

                    # Get model's response with timeout
                    print("Preparing to generate LLM response...")
                    prompt = f"{system_prompt}\n\nQuery: {current_query}"
                    try:
                        response = await generate_with_timeout(client, prompt)
                        response_text = response.text.strip()
                        print(f"LLM Response: {response_text}")

                        # Find the FUNCTION_CALL line in the response
                        for line in response_text.split("\n"):
                            line = line.strip()
                            if line.startswith("FUNCTION_CALL:") or line.startswith(
                                "FINAL_ANSWER:"
                            ):
                                response_text = line
                                break

                    except Exception as e:
                        print(f"Failed to get LLM response: {e}")
                        break

                    if response_text.startswith("FUNCTION_CALL:"):
                        _, function_info = response_text.split(":", 1)
                        parts = [p.strip() for p in function_info.split("|")]
                        func_name, params = parts[0], parts[1:]
                        print("Step:6 - Found FUNCTION_CALL and Parameters")
                        print(f"\nDEBUG: Function name: {func_name}")
                        print(f"DEBUG: Raw parameters: {params}")

                        try:
                            # Find the matching tool to get its input schema
                            tool = next((t for t in tools if t.name == func_name), None)
                            if not tool:
                                print(
                                    f"DEBUG: Available tools: {[t.name for t in tools]}"
                                )
                                raise ValueError(f"Unknown tool: {func_name}")

                            print(f"DEBUG: Found tool: {tool.name}")
                            print(f"DEBUG: Tool schema: {tool.inputSchema}")

                            # Prepare arguments according to the tool's input schema
                            arguments = {}
                            schema_properties = tool.inputSchema.get("properties", {})
                            print(f"DEBUG: Schema properties: {schema_properties}")

                            for param_name, param_info in schema_properties.items():
                                if not params:  # Check if we have enough parameters
                                    break  # Some parameters might be optional

                                value = params.pop(
                                    0
                                )  # Get and remove the first parameter
                                param_type = param_info.get("type", "string")

                                print(
                                    f"DEBUG: Converting parameter {param_name} with value {value} to type {param_type}"
                                )

                                # Convert the value to the correct type based on the schema
                                if param_type == "integer":
                                    arguments[param_name] = int(value)
                                elif param_type == "number":
                                    arguments[param_name] = float(value)
                                elif param_type == "array":
                                    # Handle array input - this is for the slides_data parameter
                                    import json

                                    if isinstance(value, str):
                                        try:
                                            # Try to parse as JSON
                                            arguments[param_name] = json.loads(value)
                                        except:
                                            # If not valid JSON, try to evaluate as Python literal
                                            import ast

                                            arguments[param_name] = ast.literal_eval(
                                                value
                                            )
                                else:
                                    arguments[param_name] = str(value)

                            # Handle any remaining parameters as optiona                l
                            print("Step:7 - Converted all parameters to proper types")
                            print(f"DEBUG: Final arguments: {arguments}")
                            print(f"DEBUG: Calling tool {func_name}")

                            result = await session.call_tool(
                                func_name, arguments=arguments
                            )
                            print(f"DEBUG: Raw result: {result}")

                            # Get the full result content
                            if hasattr(result, "content"):
                                print(f"DEBUG: Result has content attribute")
                                # Handle multiple content items
                                if isinstance(result.content, list):
                                    iteration_result = [
                                        (
                                            item.text
                                            if hasattr(item, "text")
                                            else str(item)
                                        )
                                        for item in result.content
                                    ]
                                else:
                                    iteration_result = str(result.content)
                            else:
                                print(f"DEBUG: Result has no content attribute")
                                iteration_result = str(result)

                            print(f"DEBUG: Final iteration result: {iteration_result}")

                            # Format the response based on result type
                            if isinstance(iteration_result, list):
                                result_str = f"[{', '.join(iteration_result)}]"
                            else:
                                result_str = str(iteration_result)

                            # Store the file path if this is the first iteration
                            if (
                                iteration == 0
                                and func_name == "create_keynote_with_text"
                            ):
                                user_home = os.path.expanduser("~")
                                keynote_file_path = f"{user_home}/Desktop/my_new.key"

                            iteration_response.append(
                                f"In iteration {iteration + 1}, you called {func_name} with {arguments} parameters, "
                                f"and the function returned {result_str}."
                            )
                            last_response = iteration_result

                        except Exception as e:
                            print(f"DEBUG: Error details: {str(e)}")
                            print(f"DEBUG: Error type: {type(e)}")
                            import traceback

                            traceback.print_exc()
                            iteration_response.append(
                                f"Error in iteration {iteration + 1}: {str(e)}"
                            )
                            break

                    elif response_text.startswith("FINAL_ANSWER:"):
                        print("\n=== Agent Execution Complete ===")
                        print(f"Final answer: {response_text}")
                        break

                    iteration += 1

    except Exception as e:
        print(f"Error in main execution: {e}")
        import traceback

        traceback.print_exc()
    finally:
        reset_state()  # Reset at the end of main


if __name__ == "__main__":
    asyncio.run(main())
