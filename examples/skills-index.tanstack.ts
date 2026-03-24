/**
 * TanStack Start API route that generates /.well-known/agent-skills/index.json.
 * Runs at request time.
 *
 * Scans public/.well-known/agent-skills/ for skill directories, parses YAML frontmatter
 * from each SKILL.md, computes SHA-256 digests, and outputs a JSON index per the
 * Agent Skills Discovery spec (v0.2.0).
 *
 * This implementation generates `type: "skill-md"` entries only. Archive-based
 * skills (`type: "archive"`) require separate tooling to create and register.
 *
 * Usage: Place this file at app/routes/.well-known/agent-skills/index.json.ts
 * Skills: Place skill directories at public/.well-known/agent-skills/{name}/SKILL.md
 *
 * Requires: gray-matter (npm install gray-matter)
 */
import { createHash } from "crypto";
import { readdir, readFile } from "fs/promises";
import { join } from "path";
import matter from "gray-matter";
import { createAPIFileRoute } from "@tanstack/react-start/api";

interface Skill {
	name: string;
	type: "skill-md";
	description: string;
	url: string;
	digest: string;
}

const SCHEMA_URI = "https://schemas.agentskills.io/discovery/0.2.0/schema.json";

/** SHA-256 digest of a buffer, formatted as sha256:{hex} */
function sha256(data: Buffer): string {
	return `sha256:${createHash("sha256").update(data).digest("hex")}`;
}

export const APIRoute = createAPIFileRoute("/.well-known/agent-skills/index.json")({
	GET: async () => {
		const skillsDir = join(process.cwd(), "public/.well-known/agent-skills");

		let entries;
		try {
			entries = await readdir(skillsDir, { withFileTypes: true });
		} catch (error) {
			if ((error as NodeJS.ErrnoException).code === "ENOENT") {
				return Response.json({ $schema: SCHEMA_URI, skills: [] });
			}
			throw error;
		}

		const skillDirs = entries.filter((e) => e.isDirectory());
		const skills: Skill[] = [];

		for (const dir of skillDirs) {
			const skillPath = join(skillsDir, dir.name, "SKILL.md");

			try {
				const content = await readFile(skillPath);
				const { data } = matter(content.toString("utf-8"));

				if (data.name && data.description) {
					skills.push({
						name: data.name,
						type: "skill-md",
						description: data.description,
						url: `/.well-known/agent-skills/${dir.name}/SKILL.md`,
						digest: sha256(content),
					});
				} else {
					console.warn(
						`Skill ${dir.name} missing required frontmatter (name/description)`,
					);
				}
			} catch (error) {
				if ((error as NodeJS.ErrnoException).code !== "ENOENT") {
					console.warn(`Failed to parse skill ${dir.name}:`, error);
				}
			}
		}

		skills.sort((a, b) => a.name.localeCompare(b.name));

		return Response.json({ $schema: SCHEMA_URI, skills });
	},
});
