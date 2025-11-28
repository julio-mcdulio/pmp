# pmp

A simple prompt management tool supporting different storage backends.

## Table of Contents

- [Quickstart](#quickstart)
- [Storage Plugins](#storage-plugins)
- [Examples](#examples)
- [Use with other tools](#use-with-other-tools)

## Quickstart

Install `pmp` using `uv` or `pip`. The project requires Python 3.10 or higher.

```bash
# With uv
$ uv pip install -e .

# Or with regular pip
$ pip install -e .
```

For development, install with test dependencies:

```bash
$ uv pip install -e ".[test]"
```

### Configuration

Configure pmp by setting the backend and storage location. The file backend stores prompts as JSON files, while the sqlite backend uses a SQLite database.

```bash
$ pmp config set backend file
backend = file

$ pmp config set backends.file.path ~/.pmp/store
backends.file.path = ~/.pmp/store
```

Alternatively, create a profile for different storage configurations:

```bash
$ pmp config profile add local --backend file --path ~/.pmp/local
profile "local" updated

$ pmp config profile add remote --backend sqlite --path ~/.pmp/remote.db
profile "remote" updated

$ pmp config profile use local
profile "local" activated
```

### Storage Plugins

`pmp` supports storage plugins that extend the default backends with additional functionality. Storage plugins use the pluggy plugin system and can be installed as optional dependencies.

#### dotprompt

The `dotprompt` storage plugin provides support for the [dotprompt](https://github.com/google/dotprompt) file format, which stores prompts as files with YAML frontmatter and a template body.

This format is compatible with tools that use the dotprompt specification and allows prompts to be stored in a human-readable format that can be easily edited and version controlled.

To install the dotprompt plugin, include the dotprompt extra when installing pmp:

```bash
$ uv pip install -e ".[dotprompt]"
```

Or with regular pip:

```bash
$ pip install -e ".[dotprompt]"
```

Once installed, the dotprompt plugin is automatically available. Configure it by setting the backend to use the dotprompt storage format and specifying a storage path:

```bash
$ pmp config set backend dotprompt
backend = dotprompt

$ pmp config set backends.dotprompt.path ~/.pmp/dotprompts
backends.dotprompt.path = ~/.pmp/dotprompts
```

The dotprompt plugin stores prompts as files with the .prompt extension. Each prompt file contains YAML frontmatter for metadata followed by the template body. When you add a prompt, the plugin automatically merges provided metadata into the frontmatter and creates a properly formatted dotprompt file.

```bash
$ pmp add greeting --content "Hello, {{name}}!" --tag "chat" --model "gpt-4"
prompt "greeting" version 1 created
```

The resulting file will contain the metadata in YAML frontmatter and the template in the body, making it easy to edit prompts directly in a text editor or include them in version control systems.

The dotprompt plugin maintains version history by storing each version in separate files and tracking version metadata. When you update a prompt, a new version is created only if the content hash changes, ensuring that identical content does not create duplicate versions.

## Examples

### Adding Prompts

Add a prompt with content, tags, and an associated model:

```bash
$ pmp add demo --content "You are a helpful assistant" --tag "chat,general" --model "gpt-4"
prompt "demo" version 1 created
```

### Retrieving Prompts

Retrieve a prompt in different formats:

```bash
$ pmp get demo
You are a helpful assistant

$ pmp get demo --format json
{
  "name": "demo",
  "version": 1,
  "content": "You are a helpful assistant",
  "metadata": {
    "tags": [
      "chat",
      "general"
    ],
    "model": "gpt-4"
  },
  "created_at": "2025-11-27T22:03:40+00:00"
}

$ pmp get demo --version 1 --format yaml
name: demo
version: 1
content: You are a helpful assistant
metadata:
  tags:
  - chat
  - general
  model: gpt-4
created_at: '2025-11-27T22:03:40+00:00'
```

### Updating Prompts

Update an existing prompt to create a new version:

```bash
$ pmp update demo --content "You are an expert assistant" --tag "expert,chat"
prompt "demo" version 2 created
```

### Listing Prompts

List all prompts:

```bash
$ pmp list
demo

$ pmp list --long
NAME  VERSION  TAGS         MODEL  UPDATED
----  -------  -----------  -----  -------------------------
demo  2        expert,chat  gpt-4  2025-11-27T22:03:49+00:00

$ pmp list --format json
[
  {
    "name": "demo",
    "latest_version": 2,
    "updated_at": "2025-11-27T22:03:49+00:00",
    "metadata": {
      "tags": [
        "expert",
        "chat"
      ],
      "model": "gpt-4"
    }
  }
]
```

Filter prompts by tag or model:

```bash
$ pmp list --tag expert
demo
test2

$ pmp list --model gpt-4
demo
```

### Deleting Prompts

Delete a specific version or all versions of a prompt:

```bash
$ pmp delete demo --version 1
prompt "demo" version 1 deleted

$ pmp delete demo --force
prompt "demo" deleted versions [2, 3]
```

### Reading from Files

Read prompt content from a file:

```bash
$ pmp add my-prompt --file prompt.txt --tag "production"
prompt "my-prompt" version 1 created
```

### Viewing Configuration

View and modify configuration:

```bash
$ pmp config get backend
file

$ pmp config list
backend = "file"
profile = "local"

[backends]

[backends.file]
path = "~/.pmp/store"

[profiles]

[profiles.local]
backend = "file"
path = "~/.pmp/local"

[profiles.remote]
backend = "sqlite"
path = "~/.pmp/remote.db"
```

### Command Overrides

Override the active profile or backend for a single command:

```bash
$ pmp --profile remote add temp-prompt --content "Temporary prompt"
prompt "temp-prompt" version 1 created

$ pmp --backend sqlite list
test-sqlite
```

## Use with other tools

pmp prompts can be easily used with other CLI tools. Here are examples using [llm](https://github.com/simonw/llm):

```bash
$ echo "Python is a programming language" | llm "$(pmp get summarize)"
Python is a versatile, high-level programming language known for its easy readability and wide range of applications.
```

```bash
$ echo "def add(a, b): return a+b" | llm "$(pmp get short-review)"
The given code defines a simple function named add that takes two parameters, a and b, and returns their sum. It uses a concise format with a single-line return statement, which is clear and efficient for its intended purpose. However, it lacks type annotations and documentation, which could improve its usability and readability, especially in larger codebases.
```

```bash
$ llm -s "$(pmp get explain-code)" "def square(x): return x*x"
The function square(x) takes an input x and returns its square by multiplying x by itself.
```

Chain multiple pmp calls together using pipes:

```bash
$ PROMPT=$(pmp list --tag code | head -1 | xargs pmp get)
$ echo "def add(a,b): return a+b" | llm -s "$PROMPT"
```

This uses pipes to find prompts tagged with "code", selects the first one, retrieves it, then uses it as a system prompt with llm.

Generate a prompt using llm and store it back in pmp:

```bash
$ pmp get generate-prompt | llm | pmp add python-reviewer --content "$(cat)" --tag "code,review"
prompt "python-reviewer" version 1 created
```

This retrieves a prompt from pmp, uses it with llm to generate a new prompt, then stores the result back into pmp.
