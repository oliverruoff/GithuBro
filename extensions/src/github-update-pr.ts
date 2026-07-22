import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { failure, gh, requiredEnv, result } from "./shared.js";

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "github_update_pr", label: "Update GitHub PR",
    description: "Update the title and/or body of an existing PR.",
    parameters: Type.Object({
      pr_number: Type.Integer({ minimum: 1 }), title: Type.Optional(Type.String({ minLength: 1 })),
      body: Type.Optional(Type.String({ minLength: 1 })),
    }),
    async execute(_id, params, signal) {
      try {
        if (params.title === undefined && params.body === undefined) throw new Error("title or body is required");
        const args = ["pr", "edit", String(params.pr_number), "--repo", requiredEnv("GITHUB_REPO")];
        if (params.title !== undefined) args.push("--title", params.title);
        if (params.body !== undefined) args.push("--body", params.body);
        await gh(args, signal);
        const url = await gh(["pr", "view", String(params.pr_number), "--repo", requiredEnv("GITHUB_REPO"), "--json", "url", "--jq", ".url"], signal);
        return result({ ok: true, url });
      } catch (error) { return failure(error); }
    },
  });
}
