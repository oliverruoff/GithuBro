import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

export function requiredEnv(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`${name} is required`);
  return value;
}

export async function gh(args: string[], signal?: AbortSignal): Promise<string> {
  const token = requiredEnv("GITHUB_PAT");
  const { stdout } = await execFileAsync("gh", args, {
    env: { ...process.env, GH_TOKEN: token, GITHUB_TOKEN: token },
    maxBuffer: 5 * 1024 * 1024,
    signal,
  });
  return stdout.trim();
}

export function result(value: unknown) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(value) }],
    details: value,
  };
}

export function failure(error: unknown) {
  const message = error instanceof Error ? error.message : String(error);
  return result({ ok: false, error: message });
}
