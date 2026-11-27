# Autotag (PDFix)

A Docker image that automatically tags a PDF using a PDFix layout template JSON and the matching PDFix SDK version from 8.4.1 up; for other or missing versions the latest PDFix SDK version is used.

## Table of Contents

- [Autotag (PDFix)](#autotag-pdfix)
  - [Getting started](#getting-started)
  - [Usage](#usage)
  - [Commands](#commands)
  - [Arguments](#arguments)
  - [How it works](#how-it-works)
  - [Exit codes](#exit-codes)
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

Option without a command: `--versions` prints the PDFix SDK versions in the image (one per line, oldest first) and exits.

## Arguments

### `tag`

| Option | Required | Type / expected value | Description |
|---|:---:|---|---|
| `--input`, `-i` | yes | Path to an existing `.pdf` file | Input PDF |
| `--output`, `-o` | yes | Path for the output `.pdf` file | Output PDF |
| `--template`, `-t` | yes | Path to an existing `.json` layout template file | PDFix layout template JSON |
| `--name` | no | String (PDFix account license name) | PDFix license name |
| `--key` | no | String (PDFix account license key) | PDFix license key |

## How it works

- The PDF is tagged with PDFix SDK from the layout template, using the SDK version written in the template (`sdk_version` in its metadata); without it, or for an unknown version, the newest SDK in the image is used. `--versions` lists the versions in the image.
- **`tag` replaces the structure:** existing tags, the structure tree and artifact marks are removed and the document is tagged again from the template.
- Password-protected PDFs are not supported: the PDFix SDK command line in the image ignores the password, so remove it first (error 30).
- **Checks before processing:** output extension (11) and folder (12), input (13), template (14, 15), then tagging.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Unexpected error (`Failed to run the program:` + traceback) |
| 10 | Failed to parse arguments. Please check the usage and try again |
| 11 | Output file must be PDF document |
| 12 | Output folder does not exist |
| 13 | Input file must be an existing PDF document |
| 14 | PDFix layout template must be an existing JSON file |
| 15 | PDFix layout template is not a valid JSON file |
| 20 | Failed to tag PDF document |
| 30 | PDF document is password-protected. Remove the password with another action first |

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

