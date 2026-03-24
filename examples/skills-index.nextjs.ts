/**
 * Next.js Route Handler that generates /.well-known/agent-skills/index.json.
 * Runs at build time when using static export, or at request time (cached via route config).
 *
 * Scans public/.well-known/agent-skills/ for skill directories, parses YAML frontmatter
 * from each SKILL.md, collects all files with SHA-256 digests, and outputs a JSON
 * index per the Agent Skills Discovery spec (v0.2.0).
 *
 * Usage: Place this file at app/.well-known/agent-skills/index.json/route.ts
 * Skills: Place skill directories at public/.well-known/agent-skills/{name}/SKILL.md
 *
 * Requires: gray-matter (npm install gray-matter)
 */
import { createHash } from "crypto";
import { readdir, readFile } from "fs/promises";
import { join, relative } from "path";
import matter from "gray-matter";

interface FileEntry {
	path: string;
	digest: string;
}

interface Skill {
	name: string;
	description: string;
	digest: string;
	files: FileEntry[];
}

/** SHA-256 digest of a buffer, formatted as sha256:{hex} */
function sha256(data: Buffer): string {
	return `sha256:${createHash("sha256").update(data).digest("hex")}`;
}

/** Compute the skill-level digest from sorted file entries */
function computeSkillDigest(files: FileEntry[]): string {
	const sorted = [...files].sort((a, b) => a.path.localeCompare(b.path));
	const manifest = sorted
		.map((f) => `${f.path}\0${f.digest.slice("sha256:".length)}\n`)
		.join("");
	return sha256(Buffer.from(manifest, "utf-8"));
}

/** Recursively collect all files with digests, returning paths relative to baseDir */
async function collectFiles(
	dir: string,
	baseDir: string,
): Promise<FileEntry[]> {
	const entries = await readdir(dir, { withFileTypes: true });
	const files: FileEntry[] = [];

	for (const entry of entries) {
		const fullPath = join(dir, entry.name);
		if (entry.isDirectory()) {
			files.push(...(await collectFiles(fullPath, baseDir)));
		} else if (entry.isFile()) {
			const content = await readFile(fullPath);
			files.push({
				path: relative(baseDir, fullPath),
				digest: sha256(content),
			});
		}
	}

	return files;
}

// Static generation - pre-render at build time
export const dynamic = "force-static";

export async function GET() {
	const skillsDir = join(process.cwd(), "public/.well-known/agent-skills");

	let entries;
	try {
		entries = await readdir(skillsDir, { withFileTypes: true });
	} catch (error) {
		if ((error as NodeJS.ErrnoException).code === "ENOENT") {
			return Response.json({ version: "0.2.0", skills: [] });
		}
		throw error;
	}

	const skillDirs = entries.filter((e) => e.isDirectory());
	const skills: Skill[] = [];

	for (const dir of skillDirs) {
		const skillDirPath = join(skillsDir, dir.name);
		const skillPath = join(skillDirPath, "SKILL.md");

		try {
			const content = await readFile(skillPath, "utf-8");
			const { data } = matter(content);

			if (data.name && data.description) {
				const allFiles = await collectFiles(skillDirPath, skillDirPath);
				const skillMd = allFiles.find((f) => f.path === "SKILL.md");
				const rest = allFiles
					.filter((f) => f.path !== "SKILL.md")
					.sort((a, b) => a.path.localeCompare(b.path));
				const files = skillMd ? [skillMd, ...rest] : rest;

				skills.push({
					name: data.name,
					description: data.description,
					digest: computeSkillDigest(files),
					files,
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

	return Response.json({ version: "0.2.0", skills });
}
