# paste.py
<a href="https://kuma.fosscu.org/status/pastepy" target="_blank"><img src="https://badgen.net/badge/status/paste.py/green?icon=lgtm" alt=""></a>
<hr>

paste.py 🐍 - A pastebin written in python.

<hr>

## Uasge:

### Uisng CLI
> cURL is required to use the CLI.

- Paste a file named 'file.txt'

```bash
curl -X POST -F "file=@file.txt" https://paste.fosscu.org/file
```

- Paste from stdin

```bash
echo "Hello, world." | curl -X POST -F "file=@-" https://paste.fosscu.org/file
```

- Delete an existing paste

```bash
curl -X DELETE https://paste.fosscu.org/paste/<id>
```

### Using the web interface:
[Go here](https://paste.fosscu.org/web)

<hr>

For info API usage and shell functions, see the [website](https://paste.fosscu.org).