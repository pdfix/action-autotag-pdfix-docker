# Autotag (PDFix)

A Docker image that automatically tags a PDF using a PDFix layout template JSON and the matching PDFix SDK version.

## Table of Contents

- [Autotag (PDFix)](#autotag-pdfix)
  - [Getting started](#getting-started)
  - [Usage](#usage)
  - [Commands](#commands)
  - [Arguments](#arguments)
  - [Examples](#examples)
  - [Notes](#notes)
  - [Help \& support](#help--support)
  - [Licenses](#licenses)

## Getting started

You need Docker installed. The first run downloads the image and may take longer than later runs.

## Usage

Mount a folder into the container and run a subcommand:

```bash
docker run --rm -v "$(pwd)":/data -w /data pdfix/autotag-pdfix:latest <command> [options]
```

## Commands

- `tag`: Tag a PDF using a PDFix layout template JSON

## Arguments

### `tag`

| Option | Required | Type / expected value | Description |
|---|:---:|---|---|
| `--input`, `-i` | yes | Path to an existing `.pdf` file | Input PDF |
| `--output`, `-o` | yes | Path for the output `.pdf` file | Output PDF |
| `--template`, `-t` | yes | Path to an existing `.json` layout template file | PDFix layout template JSON |
| `--name` | no | String (PDFix account license name) | PDFix license name |
| `--key` | no | String (PDFix account license key) | PDFix license key |

## Examples

Tag `input.pdf` using `template.json`:

```bash
docker run --rm -v "$(pwd)":/data -w /data pdfix/autotag-pdfix:latest \
  tag --name "${LICENSE_NAME}" --key "${LICENSE_KEY}" \
  -i /data/input.pdf -t /data/template.json -o /data/output.pdf
```

## Notes

- The template JSON may require a specific PDFix SDK version; the image selects a compatible SDK automatically.

## Help & support

For PDFix SDK licensing or issues, contact `support@pdfix.net`.

## Licenses

- [PDFix Terms](https://pdfix.net/terms)

Trial versions of the PDFix SDK may apply watermarks and redact random content in the output PDF.
