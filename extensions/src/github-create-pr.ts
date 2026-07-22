import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { failure, gh, requiredEnv, result } from "./shared.js";

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "github_create_pr", label: "Create GitHub PR",
    description: "Open a pull request for the current githubro branch.",
    parameters: Type.Object({
      title: Type.String({ minLength: 1 }), body: Type.String({ minLength: 1 }),
      base: Type.Optional(Type.String()), head: Type.Optional(Type.String()),
    }),
    async execute(_id, params, signal) {
      try {
        const repo = requiredEnv("GITHUB_REPO");
        const expectedBase = requiredEnv("GITHUB_PR_TARGET");
        const base = params.base ?? expectedBase;
        if (base !== expectedBase) throw new Error(`PR base must be ${expectedBase}`);
        const head = params.head ?? (await gh(["branch", "--show-current"], signal));
        if (!/^agent\/\d+-/.test(head)) throw new Error("PR head must be a githubro agent branch");
        const url = await gh(["pr", "create", "--repo", repo, "--base", base, "--head", head,
          "--title", params.title, "--body", params.body], signal);
        const number = Number(url.match(/\/pull\/(\d+)/)?.[1]);
        return result({ ok: true, number, url });
      } catch (error) { return failure(error); }
    },
  });
}
