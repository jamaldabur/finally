---
name: litellm-stream
description: Use this to write code to call an LLM using LiteLLM and OpenRouter
---

# Calling an LLM

These instructions allow you write code to call an LLM.  
This method uses LiteLLM and OpenRouter.

## Setup

The OPENROUTER_API_KEY must be set in the .env file and loaded in as an environment variable.  

The uv project must include litellm and pydantic.
`uv add litellm pydantic`

## Code snippets

Use code like these examples.

### Imports and constants

```python
from litellm import completion
MODEL = "openrouter/openai/gpt-oss-120b"
```

### Code to call for a text response

```python
response = completion(model=MODEL, messages=messages, reasoning_effort="low")
result = response.choices[0].message.content
```

### Code to call for a Structured Outputs response

```python
response = completion(model=MODEL, messages=messages, response_format=MyBaseModelSubclass, reasoning_effort="low", stream=True)
json_string = ""
for chunk in response:
    content = chunk.choices[0].delta.content
    if content:
        print(content, end="", flush=True) 
        json_string += content
result_as_object = MyBaseModelSubclass.model_validate_json(json_string)
```