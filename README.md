# Agent Skills Discovery via Well-Known URIs

**Status**: Draft  
**Version**: 0.2.0  
**Published Date**: 2026-01-17  
**Updated Date**: 2026-02-13

## Table of Contents

1. [Abstract](#abstract)
2. [Changelog](#changelog)
3. [Terminology](#terminology)
4. [Problem](#problem)
5. [Solution](#solution)
6. [URI Structure](#uri-structure)
7. [Skill Directory Contents](#skill-directory-contents)
8. [Progressive Disclosure](#progressive-discovery)
9. [Discovery Index](#discovery-index)
10. [Integrity and Verification](#integrity-and-verification)
11. [Package Distribution](#package-distribution)
12. [Examples](#examples)
13. [HTTP Considerations](#http-considerations)
14. [Client Implementation](#client-implementation)
15. [Security Considerations](#security-considerations)
16. [Relationship to Existing Specifications](#relationship-to-existing-specifications)
17. [References](#references)

## Abstract

This document defines a mechanism for discovering [Agent Skills](https://agentskills.io/) using the `.well-known` URI path prefix as specified in [RFC 8615](https://datatracker.ietf.org/doc/html/rfc8615). Skills are currently scattered across GitHub repositories, documentation sites, in other sources. A well-known URI provides a predictable location for agents and tools to discover skills published by an organization or project.

## Changelog

#### v0.2.0

- add `version` field to `index.json`; define strict `M.m.p` versioning scheme
- add per-skill and per-file content digests (`digest` field) for integrity verification
- `files` array entries are now objects with `path` and `digest` (breaking change from v0.1.0 string arrays)
- add optional `package` property for archive-based distribution
- add RFC 2119 / RFC 8174 keyword conventions
- strengthen script execution guidance — clients SHALL NOT execute scripts by default
- add "Integrity and Verification" section defining digest construction and verification
- add "Package Distribution" section
- add backward-compatibility guidance for v0.1.0 clients

#### v0.1.0

- initial draft

## Terminology

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119) [RFC 8174](https://datatracker.ietf.org/doc/html/rfc8174) when, and only when, they appear in all capitals, as shown here.

## Problem

Agent Skills give AI agents domain-specific capabilities through structured instructions, scripts, and resources. Today, discovering skills requires:

- Searching GitHub repositories
- Reading vendor documentation
- Following links shared on social media
- Manual configuration by end users

There is no standard way to answer: "What skills does example.com publish?"

## Solution

Register `skills` as a well-known URI suffix. Organizations can publish skills at:

```
https://example.com/.well-known/skills/
```

This provides a **single, predictable location** where agents and tooling can discover and fetch skills without prior configuration.

## URI Structure

The well-known skills path uses this hierarchy:

```
/.well-known/skills/index.json          # Required: skills index
/.well-known/skills/{skill-name}/       # Skill directory
/.well-known/skills/{skill-name}/SKILL.md
```

The `{skill-name}` segment must conform to the [Agent Skills specification](https://agentskills.io/specification):

- 1-64 characters
- Lowercase alphanumeric and hyphens only (`a-z`, `0-9`, `-`)
- Must not start or end with a hyphen
- Must not contain consecutive hyphens

## Skill Directory Contents

Each skill directory must contain a `SKILL.md` file and may include supporting resources:

```
/.well-known/skills/pdf-processing/
├── SKILL.md           # Required: instructions + metadata
├── scripts/           # Optional: executable code
│   └── extract.py
├── references/        # Optional: documentation
│   └── REFERENCE.md
└── assets/            # Optional: templates, data files
    └── schema.json
```

The `SKILL.md` file must contain YAML frontmatter with `name` and `description` fields, followed by Markdown instructions.

## Progressive Disclosure

Skills use a three-level loading pattern to manage context efficiently:

| Level | What | When Loaded | Token Cost |
|-------|------|-------------|------------|
| 1 | `name` + `description` from index | At startup or when probing | ~100 tokens per skill |
| 2 | Full `SKILL.md` body | When skill is activated | < 5k tokens recommended |
| 3 | Referenced files (scripts, references, assets) | On demand, as needed | Unlimited |

**Level 1: Index metadata.** Agents fetch `index.json` to learn what skills exist and prefetch their files. Only the name and description are loaded into context initially.

**Level 2: Skill instructions.** When a task matches a skill's description, the agent fetches `SKILL.md` and loads its full instructions into context.

**Level 3: Supporting resources.** The `SKILL.md` body references additional files via relative links. Agents fetch these on demand as the task requires - a form-filling task might need `references/FORMS.md`, while a simple extraction task does not.

This pattern means a skill can bundle extensive reference material without paying a context cost upfront. Agents follow links as needed, fetching only what the current task requires.

### Example: Progressive loading

````yaml
---
name: pdf-processing
description: Extract text and tables from PDF files. Use when working with PDFs or document extraction.
---

# PDF Processing

## Quick Start

Use pdfplumber to extract text:

```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    text = pdf.pages[0].extract_text()
```

## Form Filling

For filling PDF forms, see [references/FORMS.md](references/FORMS.md).

## Advanced Table Extraction

For complex tables with merged cells, see [references/TABLES.md](references/TABLES.md) and run `scripts/extract_tables.py`.
````

An agent handling "extract text from this PDF" loads `SKILL.md` and stops there. An agent handling "fill out this tax form" follows the link to `references/FORMS.md`. The table extraction script and reference stay unfetched until needed.

## Discovery Index

Publishers MUST provide an index at `/.well-known/skills/index.json`. The index enumerates all available skills and their files, enabling clients to discover and prefetch skill resources in a single request.

### Versioning

The index MUST include a top-level `version` field conforming to `M.m.p` format (major.minor.patch), where M, m, and p are non-negative integers with no leading zeros.

- **Major** (`M`): Incremented for backward-incompatible changes to the index schema. Clients encountering an unrecognized major version SHOULD reject the index and warn the user.
- **Minor** (`m`): Incremented for backward-compatible additions (new optional fields, new sections). Clients MUST ignore unrecognized fields.
- **Patch** (`p`): Incremented for clarifications or editorial changes that do not affect the schema.
- Pre-1.0 versions (major = 0) MAY include breaking changes in minor releases.

Clients MUST parse the `version` field before processing the index. If `version` is absent, clients SHOULD treat the index as v0.1.0 for backward compatibility.

### Index Format

```json
{
  "version": "0.2.0",
  "skills": [
    {
      "name": "wrangler",
      "description": "Deploy and manage Cloudflare Workers projects.",
      "digest": "sha256:a1b2c3d4...",
      "files": [
        { "path": "SKILL.md", "digest": "sha256:d4e5f6a7..." },
        { "path": "references/commands.md", "digest": "sha256:7a8b9c0d..." },
        { "path": "references/configuration.md", "digest": "sha256:0d1e2f3a..." }
      ],
      "package": {
        "url": "https://example.com/.well-known/skills/wrangler.tar.gz",
        "digest": "sha256:f1e2d3c4..."
      }
    },
    {
      "name": "code-review",
      "description": "Review code for bugs, security issues, and best practices.",
      "digest": "sha256:c4d5e6f7...",
      "files": [
        { "path": "SKILL.md", "digest": "sha256:a7b8c9d0..." }
      ]
    }
  ]
}
```

The index contains a top-level `version` field and a `skills` array.

**Top-level fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `version` | Yes | Index schema version in `M.m.p` format. Current version is `0.2.0`. |
| `skills` | Yes | Array of skill entries. |

**Skill entry fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Skill identifier. MUST match the directory name under `/.well-known/skills/` and conform to the [Agent Skills naming specification](https://agentskills.io/specification#name-field): 1-64 characters, lowercase alphanumeric and hyphens only, no leading/trailing/consecutive hyphens. |
| `description` | Yes | Brief description of what the skill does and when to use it. Max 1024 characters per the Agent Skills spec. |
| `digest` | Yes | SHA-256 content digest of the skill. Used for change detection and validation. See [Integrity and Verification](#integrity-and-verification). |
| `files` | Yes | Array of file objects in the skill directory. See [Files Array](#files-array). |
| `package` | No | Archive distribution object with `url` and `digest`. See [Package Distribution](#package-distribution). |

Clients derive the skill path from the `name` field directly:

```
/.well-known/skills/{name}/SKILL.md
```

For example, `"name": "wrangler"` maps to `/.well-known/skills/wrangler/SKILL.md`.

### Files Array

The `files` array lists all files in the skill directory as objects. This enables clients to prefetch and locally cache skill resources, and to verify content integrity per file.

Each file entry has these fields:

| Field | Required | Description |
|-------|----------|-------------|
| `path` | Yes | File path relative to the skill directory. |
| `digest` | Yes | `sha256:{hex}` digest of the file's raw bytes. See [Integrity and Verification](#integrity-and-verification). |

**Path requirements:**

- The array MUST be non-empty
- The array MUST include an entry with `path` value `SKILL.md`
- The `SKILL.md` entry SHOULD be first
- Paths MUST be relative to the skill directory
- Paths MUST use forward slash (`/`) as the separator
- Paths MUST NOT begin with `/` or contain `..` segments
- Paths MUST contain only printable ASCII characters (0x20-0x7E), excluding `\`, `?`, `#`, `[`, `]`, and control characters
- Each path MUST correspond to an actual file served at `/.well-known/skills/{name}/{path}`

**Example entries:**

```json
{ "path": "SKILL.md", "digest": "sha256:d4e5f6a7..." }
{ "path": "scripts/deploy.sh", "digest": "sha256:0a1b2c3d..." }
{ "path": "references/API.md", "digest": "sha256:e5f6a7b8..." }
{ "path": "assets/config.template.yaml", "digest": "sha256:9c0d1e2f..." }
```

**Caching and progressive disclosure.** Clients MAY prefetch all files listed in the `files` array for local caching. However, clients MUST NOT load all files into context simultaneously. The [progressive disclosure model](https://agentskills.io/specification#progressive-disclosure) still applies: load `SKILL.md` first, then fetch supporting resources on demand as the task requires.

### Backward Compatibility

The v0.2.0 `files` array format (objects with `path` and `digest`) is not backward-compatible with v0.1.0 (plain string arrays). Clients encountering string entries in `files` SHOULD treat them as v0.1.0 format — interpret each string as a file path with no digest available. Clients SHOULD warn when processing a v0.1.0 index that integrity verification is not possible.

Publishers SHOULD migrate to v0.2.0 to enable integrity verification for clients.

## Integrity and Verification

All digests in the index use SHA-256 and are formatted as `sha256:{hex}`, where `{hex}` is 64 lowercase hexadecimal characters.

### Per-File Digest

The digest of a file is the SHA-256 hash of the file's raw bytes, hex-encoded with the `sha256:` prefix:

```
sha256:{SHA-256(raw_bytes)}
```

Clients MUST verify downloaded file contents against the per-file digest in the index. A mismatch indicates the content is corrupted or has been tampered with; clients MUST NOT use unverified content.

### Skill-Level Digest

The skill-level digest provides a single value for change detection across all files in a skill. It is computed deterministically from the per-file digests:

1. Collect all entries from the skill's `files` array.
2. Sort entries lexicographically by `path` (byte-order, ASCII).
3. For each entry, construct a manifest line: `{path}\0{hex}\n`
   - `{path}` is the relative file path
   - `\0` is a null byte (0x00) separator
   - `{hex}` is the 64-character lowercase hex SHA-256 of the file's raw bytes (without the `sha256:` prefix)
   - `\n` is a newline (0x0A)
4. Concatenate all manifest lines in sorted order.
5. Compute SHA-256 of the resulting bytes.
6. Format as `sha256:{hex}`.

#### Worked example

Given a skill with two files:

| File | Contents (bytes) | SHA-256 |
|------|-------------------|---------|
| `SKILL.md` | `# Hello\n` (8 bytes) | `90f8ec5669cd34183b9b0fdf8b94f5efb4c3672876330f4aa76088c2b4ad17be` |
| `scripts/run.sh` | `#!/bin/sh\n` (10 bytes) | `a8076d3d28d21e02012b20eaf7dbf75409a6277134439025f282e368e3305abf` |

**Step 1-2.** Sort by path: `SKILL.md`, then `scripts/run.sh`.

**Step 3-4.** Construct the manifest (shown with escape sequences):

```
SKILL.md\x0090f8ec5669cd34183b9b0fdf8b94f5efb4c3672876330f4aa76088c2b4ad17be\n
scripts/run.sh\x00a8076d3d28d21e02012b20eaf7dbf75409a6277134439025f282e368e3305abf\n
```

**Step 5-6.** SHA-256 of the manifest bytes:

```
sha256:34f7a8c484e9991f3e71a309f31332d6335efc01f544105c4185a7c4ab12eb1e
```

Implementers can use these values to validate their digest computation.

### Verification Flows

- **Change detection**: Compare the skill-level `digest` against a locally cached value. If they match, no files have changed and the client can skip updating.
- **Individual file verification**: After downloading a file, compute its SHA-256 and compare against the per-file `digest` in the index. Reject on mismatch.
- **Post-fetch validation**: After all files are fetched or unpacked from a package, recompute the skill-level digest from the downloaded file contents and verify it matches the skill-level `digest`. This guards against partial updates or index/content desynchronization.

## Package Distribution

Publishers MAY provide an optional `package` field on a skill entry for archive-based distribution. This is useful for skills with many files where a single download is more efficient than fetching files individually.

### Package Format

```json
"package": {
  "url": "https://example.com/.well-known/skills/wrangler.tar.gz",
  "digest": "sha256:f1e2d3c4..."
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `url` | Yes | URL to a `.tar.gz` or `.zip` archive containing the skill's files. |
| `digest` | Yes | `sha256:{hex}` digest of the archive bytes. |

### Archive Structure

- The archive root corresponds to the skill directory.
- The archive MUST contain files at paths matching the `files` array entries.
- The archive MUST NOT contain path traversal sequences (`..`) or absolute paths.

### Validation

Clients fetching a package MUST validate it in this order:

1. Download the archive and compute its SHA-256.
2. Compare against `package.digest`. Reject on mismatch.
3. Unpack the archive.
4. Verify each unpacked file's digest against the corresponding per-file `digest` in the index.
5. Recompute the skill-level digest and verify it matches the skill-level `digest`.

### Distribution Guidance

Simple skills — those with only `SKILL.md` or a small number of files — SHOULD prefer individual file distribution. Individual files are easier for clients to inspect and for users to validate compared to an opaque archive.

The `package` field is OPTIONAL. Publishers MAY provide it, and clients MAY prefer fetching individual files even when `package` is available.

## Examples

### Simple skill (SKILL.md only)

A minimal skill contains just the required `SKILL.md`:

````
GET /.well-known/skills/git-workflow/SKILL.md

---
name: git-workflow
description: Follow team Git conventions for branching and commits.
---

# Git Workflow

Create feature branches from `main`:

```bash
git checkout -b feature/my-feature main
```

Commit messages use conventional commits format:

```
feat: add user authentication
fix: resolve null pointer in login
docs: update API reference
```
````

### Complex skill with resources

A skill with scripts and reference documentation:

```
/.well-known/skills/data-pipeline/
├── SKILL.md
├── scripts/
│   ├── validate.py
│   └── transform.py
├── references/
│   ├── SCHEMA.md
│   └── ERROR_CODES.md
└── assets/
    └── config.template.yaml
```

The `SKILL.md` references these files for progressive disclosure:

```yaml
---
name: data-pipeline
description: Build and validate data pipelines. Use when processing datasets or ETL workflows.
---

# Data Pipeline

## Validation

Run `scripts/validate.py` against your dataset before processing.

For schema requirements, see [references/SCHEMA.md](references/SCHEMA.md).
```

### Index with digests and package

```json
{
  "version": "0.2.0",
  "skills": [
    {
      "name": "data-pipeline",
      "description": "Build and validate data pipelines. Use when processing datasets or ETL workflows.",
      "digest": "sha256:b7e23ec29af22b0b4e41da31e868d57226121c84...",
      "files": [
        { "path": "SKILL.md", "digest": "sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e..." },
        { "path": "assets/config.template.yaml", "digest": "sha256:e3b0c44298fc1c149afbf4c899..." },
        { "path": "references/ERROR_CODES.md", "digest": "sha256:5e884898da28047151d0e56f8dc..." },
        { "path": "references/SCHEMA.md", "digest": "sha256:6ca13d52ca70c883e0f0bb101e4..." },
        { "path": "scripts/transform.py", "digest": "sha256:3c9909afec25354d551dae21590b..." },
        { "path": "scripts/validate.py", "digest": "sha256:a591a6d40bf420404a011733cfb7..." }
      ],
      "package": {
        "url": "https://example.com/.well-known/skills/data-pipeline.tar.gz",
        "digest": "sha256:9f86d081884c7d659a2feaa0c55ad015..."
      }
    }
  ]
}
```

## HTTP Considerations

Servers MUST:

- Serve `/.well-known/skills/index.json` with `application/json` content type
- Serve `SKILL.md` files with `text/markdown` or `text/plain` content type
- Support `GET` and `HEAD` methods
- Return `404 Not Found` for skills or files that do not exist

Servers SHOULD:

- Set appropriate `Cache-Control` headers

Clients MUST:

- Handle redirects (3xx responses)
- Respect cache headers

## Client Implementation

Clients discovering skills from a well-known endpoint MUST:

1. **Fetch `index.json`.** Retrieve `/.well-known/skills/index.json` to enumerate available skills and their files.

2. **Check version.** Parse the `version` field. If absent, treat the index as v0.1.0. If the major version is unrecognized, warn the user and abort. Clients MUST ignore unrecognized fields.

3. **Use digests for caching.** Compare each skill's `digest` against locally cached values. If the digest matches, the skill is unchanged and the client MAY skip fetching its files. This allows clients to efficiently detect whether any updates are needed without downloading file contents.

4. **Prefetch and verify skill files.** For skills that need updating, use the `files` array to download all resources. After downloading each file, verify its digest against the per-file `digest` in the index. Cache locally to avoid network requests during task execution.

5. **Validate skill integrity.** After all files for a skill are fetched or unpacked, recompute the skill-level digest from file contents using the [deterministic algorithm](#skill-level-digest) and verify it matches the skill's `digest` field.

6. **Apply progressive disclosure.** Load only `name` and `description` at discovery time. Load `SKILL.md` when a skill is activated. Load supporting resources (scripts, references, assets) on demand as the task requires.

7. **Resolve relative paths.** File paths in the `files` array are relative to the skill directory. Resolve against the skill URL:
   - Skill: `/.well-known/skills/wrangler/`
   - File entry path: `scripts/deploy.sh`
   - Resolved URL: `/.well-known/skills/wrangler/scripts/deploy.sh`

8. **Cache aggressively.** Skills change infrequently. Respect `Cache-Control` headers and consider caching content for the duration of a session. Use skill digests to invalidate cached content when updates are detected.

9. **Gate script execution.** Clients SHALL NOT execute files under `scripts/` by default. Clients SHALL consider implementing a permissions model that only executes scripts bundled with a skill when explicitly allowed by the user or client configuration. Consider sandboxing execution environments and restricting filesystem and network access. Never execute scripts from untrusted origins without user approval.

## Security Considerations

The security considerations from [RFC 8615 Section 4](https://datatracker.ietf.org/doc/html/rfc8615#section-4) apply. Additional considerations for skills:

- **Trust**: Skills contain instructions and executable code. Agents should only use skills from trusted origins. See the [Agent Skills security guidance](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview#security-considerations).
- **Access control**: Servers should control write access to `/.well-known/skills/` carefully, especially in shared hosting environments.
- **Script execution**: Clients SHALL NOT execute files under `scripts/` by default. Clients SHALL consider implementing a permissions model that only executes scripts bundled with a skill when explicitly allowed by the user or client configuration. Refer to the [Agent Skills specification](https://agentskills.io/specification) guidance on script execution.
- **Digest verification**: Clients MUST verify file digests after download. A digest mismatch indicates the content has been tampered with or is stale; clients MUST NOT use unverified content.
- **Archive safety**: Clients MUST validate archive digests before unpacking. Clients MUST reject archives containing path traversal sequences (`..`, absolute paths). Clients SHOULD verify total unpacked size against reasonable limits to prevent denial-of-service via decompression bombs.
- **External references**: Skills that fetch external resources introduce additional trust boundaries.

## Relationship to Existing Specifications

This document builds on:

- [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119) - Key Words for Use in RFCs to Indicate Requirement Levels
- [RFC 8174](https://datatracker.ietf.org/doc/html/rfc8174) - Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words
- [RFC 8615](https://datatracker.ietf.org/doc/html/rfc8615) - Well-Known URIs
- [Agent Skills Specification](https://agentskills.io/specification) - Skill format and structure

## References

- [Agent Skills](https://agentskills.io/) - Open standard for agent skills
- [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119) - Key Words for Use in RFCs to Indicate Requirement Levels
- [RFC 8174](https://datatracker.ietf.org/doc/html/rfc8174) - Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words
- [RFC 8615](https://datatracker.ietf.org/doc/html/rfc8615) - Well-Known Uniform Resource Identifiers
- [Claude Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
- [OpenAI Codex Skills](https://developers.openai.com/codex/skills/)
- [OpenCode Skills](https://opencode.ai/docs/skills/)
