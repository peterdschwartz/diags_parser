## E3SM Diagnostics Parser

### Install:
`pip install -e .`
Verify with `edp`

## Usage
Two entry points `parse` and `functions`
* `functions` is used to list registry of currently supported functions and their expected syntax.
* `parse` generates parsing output to a dictionary on the commandline

```bash
edp parse -s "< string to parse >"
edp parse -f "/path/to/file"
```

