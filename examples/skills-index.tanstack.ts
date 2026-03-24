/**
 * TanStack Start API route that generates /.well-known/agent-skills/index.json.
 * Runs at request time.
 *
 * Scans public/.well-known/agent-skills/ for skill directories, parses YAML frontmatter
 * from each SKILL.md, collects all files, and outputs a JSON index per the Agent Skills Discovery spec.
 *
 * Usage: Place this file at app/routes/.well-known/agent-skills/index.json.ts
 * Skills: Place skill directories at public/.well-known/agent-skills/{name}/SKILL.md
 *
 * Requires: gray-matter (npm install gray-matter)
 */
import { readdir, readFile } from "fs/promises";
import { join, relative } from "path";
import matter from "gray-matter";
import { createAPIFileRoute } from "@tanstack/react-start/api";

interface Skill {
	name: string;
	description: string;
	files: string[];
}

/** Recursively collect all files in a directory, returning paths relative to baseDir */
async function collectFiles(dir: string, baseDir: string): Promise<string[]> {
	const entries = await readdir(dir, { withFileTypes: true });
	const files: string[] = [];

	for (const entry of entries) {
		const fullPath = join(dir, entry.name);
		if (entry.isDirectory()) {
			files.push(...(await collectFiles(fullPath, baseDir)));
		} else if (entry.isFile()) {
			files.push(relative(baseDir, fullPath));
		}
	}

	return files;
}

export const APIRoute = createAPIFileRoute("/.well-known/agent-skills/index.json")({
	GET: async () => {
		const skillsDir = join(process.cwd(), "public/.well-known/agent-skills");

		let entries;
		try {
			entries = await readdir(skillsDir, { withFileTypes: true });
		} catch (error) {
			if ((error as NodeJS.ErrnoException).code === "ENOENT") {
				return Response.json({ skills: [] });
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
					// Ensure SKILL.md is first, then sort the rest
					const files = [
						"SKILL.md",
						...allFiles.filter((f) => f !== "SKILL.md").sort(),
					];

					skills.push({
						name: data.name,
						description: data.description,
						files,
					});
				} else {
					console.warn(`Skill ${dir.name} missing required frontmatter (name/description)`);
				}
			} catch (error) {
				if ((error as NodeJS.ErrnoException).code !== "ENOENT") {
					console.warn(`Failed to parse skill ${dir.name}:`, error);
				}
			}
		}

		skills.sort((a, b) => a.name.localeCompare(b.name));

		return Response.json({ skills });
	},
});
