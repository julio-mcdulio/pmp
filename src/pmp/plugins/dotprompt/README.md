## dotprompt

The `dotprompt` storage plugin provides support for the [dotprompt](https://github.com/google/dotprompt) file format, storing prompts as files with YAML frontmatter and a template body. Install it with the dotprompt extra:

```bash
$ uv pip install -e ".[dotprompt]"
```

Or with regular pip:

```bash
$ pip install -e ".[dotprompt]"
```

Once installed, configure the dotprompt backend:

```bash
$ pmp config set backend dotprompt
backend = dotprompt

$ pmp config set backends.dotprompt.path ~/.pmp/dotprompts
backends.dotprompt.path = ~/.pmp/dotprompts
```

The plugin stores prompts as `.prompt` files with YAML frontmatter for metadata and the template in the body. Metadata provided when adding prompts is automatically merged into the frontmatter, and version history is maintained by tracking content hashes.