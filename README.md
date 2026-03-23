# Agent Skills Discovery via Well-Known URIs

**Status**: Draft
**Version**: 0.2.0
**Published Date**: 2026-01-17
**Updated Date**: 2026-03-12

## Table of Contents

1. [Abstract](#abstract)
2. [Changelog](#changelog)
3. [Terminology](#terminology)
4. [Problem](#problem)
5. [Solution](#solution)
6. [URI Structure](#uri-structure)
7. [Skill Directory Contents](#skill-directory-contents)
8. [Progressive Disclosure](#progressive-disclosure)
9. [Discovery Index](#discovery-index)
10. [Integrity and Verification](#integrity-and-verification)
11. [Archive Distribution](#archive-distribution)
12. [Examples](#examples)
13. [HTTP Considerations](#http-considerations)
14. [Client Implementation](#client-implementation)
15. [Security Considerations](#security-considerations)
16. [Relationship to Existing Specifications](#relationship-to-existing-specifications)
17. [References](#references)

## Abstract

This document defines a mechanism for discovering [Agent Skills](https://agentskills.io/) using the `.well-known` URI path prefix as specified in [RFC 8615](https://datatracker.ietf.org/doc/html/rfc8615). Skills are currently scattered across GitHub repositories, documentation sites, and other sources. A well-known URI provides a predictable location for agents and tools to discover skills published by an organization or project.

## Changelog

#### v0.2.0

- rename well-known URI from `/.well-known/skills/` to `/.well-known/agent-skills/`
- replace `version` field with `$schema` URI (`https://schemas.agentskills.io/discovery/0.2.0/schema.json`)
- replace `files` array and `package` object with a flat single-artifact model: each skill entry now has `type` (`"skill-md"` or `"archive"`), `url`, and `digest`
- `digest` is now the SHA-256 of the single artifact (not a manifest-derived skill-level digest)
- add archive safety guidance: path traversal, symlinks, decompression bombs
- add URL resolution semantics per RFC 3986
- add RFC 2119 / RFC 8174 keyword conventions
- strengthen script execution guidance — clients SHALL NOT execute scripts by default
- add "Integrity and Verification" section
- add "Archive Distribution" section
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

Register `agent-skills` as a well-known URI suffix. Organizations can publish skills at:

```
https://example.com/.well-known/agent-skills/
```

This provides a **single, predictable location** where agents and tooling can discover and fetch skills without prior configuration.

## URI Structure

Publishers MUST provide an index at:

```
/.well-known/agent-skills/index.json
```

Each skill in the index includes a `url` field pointing to its artifact. While publishers conventionally host skill files under `/.well-known/agent-skills/`, the `url` field allows skills to be hosted at any location (e.g., on a CDN or at a versioned path).

Skill names MUST conform to the [Agent Skills specification](https://agentskills.io/specification):

- 1-64 characters
- Lowercase alphanumeric and hyphens only (`a-z`, `0-9`, `-`)
- MUST NOT start or end with a hyphen
- MUST NOT contain consecutive hyphens

## Skill Directory Contents

A skill consists of a required `SKILL.md` file and optional supporting resources:

```
skill-name/
├── SKILL.md           # Required: instructions + metadata
├── scripts/           # Optional: executable code
│   └── extract.py
├── references/        # Optional: documentation
│   └── REFERENCE.md
└── assets/            # Optional: templates, data files
    └── schema.json
```

Skills consisting of `SKILL.md` alone are typically distributed as individual files (`type: "skill-md"` in the index). Skills with supporting resources are distributed as archives (`type: "archive"` in the index). See [Discovery Index](#discovery-index) for details.

The `SKILL.md` file MUST contain YAML frontmatter with `name` and `description` fields, followed by Markdown instructions.

## Progressive Disclosure

Skills use a progressive loading pattern to manage context efficiently:

| Level | What | When Loaded | Token Cost |
|-------|------|-------------|------------|
| 1 | `name` + `description` from index | At startup or when probing | ~100 tokens per skill |
| 2 | Full `SKILL.md` body | When skill is activated | < 5k tokens recommended |
| 3 | Referenced files (scripts, references, assets) | On demand, as needed | Unlimited |

**Level 1: Index metadata.** Agents fetch `index.json` to learn what skills exist. Only the name and description are loaded into context initially.

**Level 2: Skill instructions.** When a task matches a skill's description, the agent fetches the skill artifact. For `type: "skill-md"` skills, this is `SKILL.md` directly. For `type: "archive"` skills, the agent downloads the archive and extracts `SKILL.md`. The full instructions are loaded into context.

**Level 3: Supporting resources.** For archive-based skills, the `SKILL.md` body references additional files via relative links. Agents load these from the unpacked archive on demand as the task requires — a form-filling task might need `references/FORMS.md`, while a simple extraction task does not.

This pattern means a skill can bundle extensive reference material without paying a context cost upfront. Agents follow links as needed, loading only what the current task requires.

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

Publishers MUST provide an index at `/.well-known/agent-skills/index.json`. The index enumerates all available skills, enabling clients to discover skills in a single request.

### Versioning

The index MUST include a top-level `$schema` field containing a URI that identifies the index schema version. The current schema URI is:

```
https://schemas.agentskills.io/discovery/0.2.0/schema.json
```

The `$schema` URI is an **opaque identifier**. Clients MUST match it against known schema URIs to determine how to process the index. The URI does not need to be resolvable, though it MAY point to a [JSON Schema](https://json-schema.org/) document that describes the index format.

Clients encountering an unrecognized `$schema` URI SHOULD warn the user and SHOULD NOT process the index. If `$schema` is absent, clients SHOULD treat the index as v0.1.0 for backward compatibility. Clients MUST ignore unrecognized fields.

### Index Format

```json
{
  "$schema": "https://schemas.agentskills.io/discovery/0.2.0/schema.json",
  "skills": [
    {
      "name": "code-review",
      "type": "skill-md",
      "description": "Review code for bugs, security issues, and best practices.",
      "url": "/.well-known/agent-skills/code-review/SKILL.md",
      "digest": "sha256:c4d5e6f7..."
    },
    {
      "name": "wrangler",
      "type": "archive",
      "description": "Deploy and manage Cloudflare Workers projects.",
      "url": "/.well-known/agent-skills/wrangler.tar.gz",
      "digest": "sha256:a1b2c3d4..."
    }
  ]
}
```

The index contains a top-level `$schema` field and a `skills` array.

**Top-level fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `$schema` | Yes | URI identifying the index schema version. See [Versioning](#versioning). |
| `skills` | Yes | Array of skill entries. |

**Skill entry fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Skill identifier. MUST conform to the [Agent Skills naming specification](https://agentskills.io/specification#name-field): 1-64 characters, lowercase alphanumeric and hyphens only, no leading/trailing/consecutive hyphens. |
| `type` | Yes | Distribution type. MUST be `"skill-md"` (single `SKILL.md` file) or `"archive"` (bundled archive). |
| `description` | Yes | Brief description of what the skill does and when to use it. Max 1024 characters per the Agent Skills spec. SHOULD match the `description` field in the skill's `SKILL.md` frontmatter. |
| `url` | Yes | URL to the skill artifact. For `type: "skill-md"`, this points to the `SKILL.md` file. For `type: "archive"`, this points to the archive file. See [URL Resolution](#url-resolution). |
| `digest` | Yes | SHA-256 content digest of the artifact at `url`, formatted as `sha256:{hex}` where `{hex}` is 64 lowercase hexadecimal characters. See [Integrity and Verification](#integrity-and-verification). |

> [!NOTE]
> In a future version, `url` may become optional for `type: "skill-md"` entries, defaulting to `/.well-known/agent-skills/{name}/SKILL.md`.

### URL Resolution

The `url` field specifies where to fetch the skill artifact. URLs are resolved per [RFC 3986 Section 5](https://datatracker.ietf.org/doc/html/rfc3986#section-5) using the index URL as the base URI. URLs may be:

- **Path-absolute** (resolved against the index origin): `/.well-known/agent-skills/code-review/SKILL.md`
- **Absolute** (fully qualified): `https://cdn.example.com/v2/skills/code-review/SKILL.md`
- **Relative** (resolved against the index URL directory): `code-review/SKILL.md`

For `type: "skill-md"`, `url` conventionally follows the pattern `/.well-known/agent-skills/{name}/SKILL.md`, though publishers MAY use any URL.

For `type: "archive"`, `url` points to the archive file. Clients SHOULD determine the archive format from the server's `Content-Type` header, falling back to the URL file extension if the header is absent or generic (e.g., `application/octet-stream`). See [Archive Distribution](#archive-distribution).

Clients encountering an unrecognized `type` value SHOULD skip that skill entry and MAY warn the user.

### Backward Compatibility

The v0.2.0 index format is not backward-compatible with v0.1.0. Key differences:

- v0.1.0 used `files` as an array of path strings with no digests. v0.2.0 removes `files` entirely, adds `type`, `url`, `digest`, and `$schema`.

Clients MUST check the `$schema` field to determine how to process the index. An unrecognized `$schema` URI indicates the index structure may have changed incompatibly; see [Versioning](#versioning).

## Integrity and Verification

All digests in the index use SHA-256 and are formatted as `sha256:{hex}`, where `{hex}` is 64 lowercase hexadecimal characters.

The `digest` field on each skill entry is the SHA-256 hash of the raw bytes of the skill's artifact:

- For `type: "skill-md"`: the SHA-256 of the `SKILL.md` file's raw bytes.
- For `type: "archive"`: the SHA-256 of the archive file's raw bytes.

```
sha256:{SHA-256(raw_bytes)}
```

### Verification

Clients MUST verify downloaded content against the `digest` in the index. A mismatch indicates the content is corrupted or has been tampered with; clients MUST NOT use unverified content.

- **Change detection**: Compare a skill's `digest` against a locally cached value. If they match, the artifact is unchanged and the client can skip re-downloading.
- **Download verification**: After downloading a skill artifact, compute its SHA-256 and compare against the `digest`. Reject on mismatch.

## Archive Distribution

Skills with supporting files (scripts, references, assets) are distributed as archives with `type: "archive"` in the index. The archive contains the full skill directory, including `SKILL.md` and all supporting resources.

### Supported Formats

Archives SHOULD be in `.tar.gz` (gzip-compressed tar) or `.zip` format. Clients MUST support at least `.tar.gz` and `.zip`. Each format has different tradeoffs:

- **`.tar.gz`**: Robust support for UNIX file permissions and symlinks.
- **`.zip`**: Limited support for UNIX file permissions and symlinks (varies by implementation). Supports partial file retrieval via HTTP range requests (useful for indexing services that need to read `SKILL.md` without downloading the full archive).

### Archive Structure

The archive contents represent the skill directory — files are placed at the archive root, not nested inside a wrapper directory.

- The archive MUST contain a `SKILL.md` file at the root.
- The archive MUST NOT contain path traversal sequences (`..`) or absolute paths.

### Archive Safety

After verifying the archive's digest (see [Integrity and Verification](#integrity-and-verification)), clients unpacking an archive MUST:

1. Reject archives containing path traversal sequences (`..`) or absolute paths.
2. Reject archives containing symlinks or hard links that resolve outside the skill directory.
3. Consider enforcing a reasonable limit on total unpacked size to prevent denial-of-service via decompression bombs.

### Distribution Guidance

Simple skills — those with only `SKILL.md` — SHOULD use `type: "skill-md"`. Archives are intended for skills with supporting files where a single download is more efficient and preserves directory structure, file permissions, and symlinks.

## Examples

### Simple skill (SKILL.md only)

A minimal skill contains just the required `SKILL.md`:

````
GET /.well-known/agent-skills/git-workflow/SKILL.md

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

A skill with scripts and reference documentation, distributed as an archive:

```
wrangler.tar.gz (archive contents)
├── SKILL.md
├── scripts/
│   ├── deploy.sh
│   └── init.sh
├── references/
│   ├── COMMANDS.md
│   └── CONFIGURATION.md
└── assets/
    └── wrangler.toml.template
```

The `SKILL.md` references these files for progressive disclosure:

```yaml
---
name: wrangler
description: Deploy and manage Cloudflare Workers projects.
---

# Wrangler

## Deployment

Run `scripts/deploy.sh` to deploy your Worker.

For available commands, see [references/COMMANDS.md](references/COMMANDS.md).
For configuration options, see [references/CONFIGURATION.md](references/CONFIGURATION.md).
```

### Discovery index

```json
{
  "$schema": "https://schemas.agentskills.io/discovery/0.2.0/schema.json",
  "skills": [
    {
      "name": "code-review",
      "type": "skill-md",
      "description": "Review code for bugs, security issues, and best practices.",
      "url": "/.well-known/agent-skills/code-review/SKILL.md",
      "digest": "sha256:c4d5e6f7..."
    },
    {
      "name": "git-workflow",
      "type": "skill-md",
      "description": "Follow team Git conventions for branching and commits.",
      "url": "/.well-known/agent-skills/git-workflow/SKILL.md",
      "digest": "sha256:a7b8c9d0..."
    },
    {
      "name": "wrangler",
      "type": "archive",
      "description": "Deploy and manage Cloudflare Workers projects.",
      "url": "/.well-known/agent-skills/wrangler.tar.gz",
      "digest": "sha256:f1e2d3c4..."
    }
  ]
}
```

## HTTP Considerations

Servers MUST:

- Serve `/.well-known/agent-skills/index.json` with `application/json` content type
- Serve `SKILL.md` files with `text/markdown` or `text/plain` content type
- Serve `.tar.gz` archives with `application/gzip` content type and `.zip` archives with `application/zip` content type
- Support `GET` and `HEAD` methods
- Return `404 Not Found` for skills or files that do not exist

Servers SHOULD:

- Set appropriate `Cache-Control` headers
- Include CORS headers (e.g., `Access-Control-Allow-Origin`) if skills are intended for consumption by browser-based clients

Clients MUST:

- Handle redirects (3xx responses)
- Respect cache headers

## Client Implementation

Clients discovering skills from a well-known endpoint MUST:

1. **Fetch `index.json`.** Retrieve `/.well-known/agent-skills/index.json` to enumerate available skills.

2. **Check schema version.** Match the `$schema` field against known schema URIs. If absent, treat the index as v0.1.0. Clients SHOULD NOT process an index with an unrecognized `$schema` URI and SHOULD warn the user. Clients MUST ignore unrecognized fields.

3. **Use digests for caching.** Compare each skill's `digest` against locally cached values. If the digest matches, the skill is unchanged and the client MAY skip re-downloading.

4. **Fetch and verify skill artifacts.** For skills that need updating:
   - For `type: "skill-md"`: Download `SKILL.md` from the skill's `url`. Compute its SHA-256 and verify against `digest`.
   - For `type: "archive"`: Download the archive from the skill's `url`. Compute its SHA-256 and verify against `digest`. Unpack the archive and validate its structure (see [Archive Safety](#archive-safety)).
   - For an unrecognized `type`: Skip the skill entry and warn the user.

5. **Apply progressive disclosure.** Load only `name` and `description` at discovery time. Load `SKILL.md` when a skill is activated. For archive-based skills, load supporting resources (scripts, references, assets) on demand as the task requires.

6. **Cache aggressively.** Skills change infrequently. Respect `Cache-Control` headers and consider caching content for the duration of a session. Use skill digests to invalidate cached content when updates are detected.

7. **Gate script execution.** Clients SHALL NOT execute files under `scripts/` by default. Clients SHALL consider implementing a permissions model that only executes scripts bundled with a skill when explicitly allowed by the user or client configuration. Consider sandboxing execution environments and restricting filesystem and network access. Never execute scripts from untrusted origins without user approval.

## Security Considerations

The security considerations from [RFC 8615 Section 4](https://datatracker.ietf.org/doc/html/rfc8615#section-4) apply. Additional considerations for skills:

- **Trust**: Skills contain instructions and executable code. Agents should only use skills from trusted origins. See the [Agent Skills security guidance](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview#security-considerations).
- **Prompt injection**: Skill content is loaded directly into agent context. A malicious `SKILL.md` can inject instructions that alter agent behavior. Clients SHOULD validate that skill artifacts originate from trusted, allowlisted domains before loading them into context.
- **Origin allowlisting**: Clients SHOULD maintain a configurable allowlist of trusted domains from which skills may be fetched. Skills from origins not on the allowlist SHOULD be rejected unless the user explicitly approves them.
- **Access control**: Servers should control write access to `/.well-known/agent-skills/` carefully, especially in shared hosting environments.
- **Script execution**: Clients SHALL NOT execute files under `scripts/` by default. Clients SHALL consider implementing a permissions model that only executes scripts bundled with a skill when explicitly allowed by the user or client configuration. Refer to the [Agent Skills specification](https://agentskills.io/specification) guidance on script execution.
- **Digest verification**: Clients MUST verify artifact digests after download. A digest mismatch indicates the content has been tampered with or is stale; clients MUST NOT use unverified content.
- **Archive safety**: Clients MUST validate archive digests before unpacking. Clients MUST reject archives containing path traversal sequences (`..`, absolute paths) or symlinks and hard links that resolve outside the skill directory. Clients SHOULD verify total unpacked size against reasonable limits to prevent denial-of-service via decompression bombs.
- **External references**: Skills that fetch external resources introduce additional trust boundaries.

## Relationship to Existing Specifications

This document builds on:

- [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119) - Key Words for Use in RFCs to Indicate Requirement Levels
- [RFC 3986](https://datatracker.ietf.org/doc/html/rfc3986) - Uniform Resource Identifier (URI): Generic Syntax
- [RFC 8174](https://datatracker.ietf.org/doc/html/rfc8174) - Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words
- [RFC 8615](https://datatracker.ietf.org/doc/html/rfc8615) - Well-Known URIs
- [Agent Skills Specification](https://agentskills.io/specification) - Skill format and structure

## References

- [Agent Skills](https://agentskills.io/) - Open standard for agent skills
- [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119) - Key Words for Use in RFCs to Indicate Requirement Levels
- [RFC 3986](https://datatracker.ietf.org/doc/html/rfc3986) - Uniform Resource Identifier (URI): Generic Syntax
- [RFC 8174](https://datatracker.ietf.org/doc/html/rfc8174) - Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words
- [RFC 8615](https://datatracker.ietf.org/doc/html/rfc8615) - Well-Known Uniform Resource Identifiers
- [Claude Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
- [OpenAI Codex Skills](https://developers.openai.com/codex/skills/)
- [OpenCode Skills](https://opencode.ai/docs/skills/)
