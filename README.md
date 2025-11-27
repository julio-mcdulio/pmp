# pmp

Install pmp using uv or pip. The project requires Python 3.10 or higher.

```bash
# With uv
uv pip install -e .

# Or with regular pip
pip install -e .
```

For development, install with test dependencies:

```bash
uv pip install -e ".[test]"
```

## Configuration

Configure pmp by setting the backend and storage location. The file backend stores prompts as JSON files, while the sqlite backend uses a SQLite database.

```bash
pmp config set backend file
```

Output: `backend = file`

```bash
pmp config set backends.file.path ~/.pmp/store
```

Output: `backends.file.path = ~/.pmp/store`

Alternatively, create a profile for different storage configurations:

```bash
pmp config profile add local --backend file --path ~/.pmp/local
```

Output: `profile "local" updated`

```bash
pmp config profile add remote --backend sqlite --path ~/.pmp/remote.db
```

Output: `profile "remote" updated`

```bash
pmp config profile use local
```

Output: `profile "local" activated`

## Adding Prompts

Add a prompt with content, tags, and an associated model:

```bash
pmp add demo --content "You are a helpful assistant" --tag "chat,general" --model "gpt-4"
```

Output: `prompt "demo" version 1 created`

## Retrieving Prompts

Retrieve a prompt in different formats:

```bash
pmp get demo
```

Output: `You are a helpful assistant`

```bash
pmp get demo --format json
```

Output:
```json
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
```

```bash
pmp get demo --version 1 --format yaml
```

Output:
```yaml
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

## Updating Prompts

Update an existing prompt to create a new version:

```bash
pmp update demo --content "You are an expert assistant" --tag "expert,chat"
```

Output: `prompt "demo" version 2 created`

## Listing Prompts

List all prompts:

```bash
pmp list
```

Output:
```
demo
```

```bash
pmp list --long
```

Output:
```
NAME  VERSION  TAGS         MODEL  UPDATED
----  -------  -----------  -----  -------------------------
demo  2        expert,chat  gpt-4  2025-11-27T22:03:49+00:00
```

```bash
pmp list --format json
```

Output:
```json
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
pmp list --tag expert
```

Output:
```
demo
test2
```

```bash
pmp list --model gpt-4
```

Output:
```
demo
```

## Deleting Prompts

Delete a specific version or all versions of a prompt:

```bash
pmp delete demo --version 1
```

Output: `prompt "demo" version 1 deleted`

```bash
pmp delete demo --force
```

Output: `prompt "demo" deleted versions [2, 3]`

## Reading from Files

Read prompt content from a file:

```bash
pmp add my-prompt --file prompt.txt --tag "production"
```

Output: `prompt "my-prompt" version 1 created`

## Viewing Configuration

View and modify configuration:

```bash
pmp config get backend
```

Output: `file`

```bash
pmp config list
```

Output:
```toml
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

## Command Overrides

Override the active profile or backend for a single command:

```bash
pmp --profile remote add temp-prompt --content "Temporary prompt"
```

Output: `prompt "temp-prompt" version 1 created`

```bash
pmp --backend sqlite list
```

Output:
```
test-sqlite
```
