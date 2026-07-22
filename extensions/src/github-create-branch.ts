import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { failure, gh, result } from "./shared.js";

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "github_create_branch", label: "Create GitHub branch",
    description: "Create and push a branch from a local base branch.",
    parameters: Type.Object({ name: Type.String({ minLength: 1 }), from: Type.Optional(Type.String({ minLength: 1 })) }),
    async execute(_id, params, signal) {
      try {
        if (!/^agent\/\d+-[a-z0-9-]+$/.test(params.name)) throw new Error("branch must match agent/<issue>-<slug>");
        const { execFile } = await import("node:child_process");
        const { promisify } = await import("node:util");
        const run = promisify(execFile);
        await run("git", ["checkout", "-b", params.name, params.from ?? process.env.GITHUB_PR_TARGET ?? "main"], { signal });
        await run("git", ["push", "-u", "origin", params.name], { signal });
        return result({ ok: true, ref: params.name });
      } catch (error) { return failure(error); }
    },
  });
}
