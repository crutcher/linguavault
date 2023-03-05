# linguavault

### Setup
```bash
$ ./grind repo bootstrap
```

Installs a python virtual environment in `.venv`

## Werdsonary

See [DEMO.md](DEMO.md)

```bash
$ ./werdsonary TERM \
     [[-c CONTEXT]] \
     [--term_language=SOURCE_LANGUAGE] \
     [--output_language=OUTPUT_LANGUAGE]
```

Example:
```bash
$ ./werdsonary cat
```

Some terms have specialized contextual definitions not in general use,
to hint towards those definitions, include one (or more) usage contexts.

```bash
$ ./werdsonary cat -c networking
```

You can also ask for the dictionary to be written in other languages.

```bash
$ ./werdsonary cat --output_language=Czech
```

```bash
$ ./werdsonary cat --output_language=Pirate
```
