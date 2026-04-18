import os
from anthropic import Anthropic

client = Anthropic()

tools = [
    {
        "name": "calculator",
        "description": "Perform basic math calculations",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Math expression to evaluate, e.g. '2 + 2'"}
            },
            "required": ["expression"]
        }
    }
]

def run_tool(name, inputs):
    if name == "calculator":
        return str(eval(inputs["expression"]))

def run_agent(user_message):
    print(f"You: {user_message}")
    messages = [{"role": "user", "content": user_message}]

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            tools=tools,
            messages=messages
        )

        if response.stop_reason == "end_turn":
            print(f"Agent: {response.content[0].text}")
            break

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"[calling tool: {block.name} with {block.input}]")
                    result = run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            messages.append({"role": "user", "content": tool_results})

if __name__ == "__main__":
    run_agent("What is 1234 multiplied by 5678?")
