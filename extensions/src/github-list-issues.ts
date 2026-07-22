import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { failure, gh, requiredEnv, result } from "./shared.js";

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "github_list_issues", label: "List GitHub issues",
    description: "List issues in the current repository by label.",
    parameters: Type.Object({
      label: Type.String({ minLength: 1 }),
      state: Type.Optional(Type.Union([Type.Literal("open"), Type.Literal("closed"), Type.Literal("all")])),
    }),
    async execute(_id, params, signal) {
      try {
        const raw = await gh(["issue", "list", "--repo", requiredEnv("GITHUB_REPO"), "--label", params.label,
          "--state", params.state ?? "open", "--limit", "100", "--json", "number,title,updatedAt"], signal);
        const issues = JSON.parse(raw || "[]").map((x: {number: number; title: string; updatedAt: string}) =>
          ({ number: x.number, title: x.title, updated_at: x.updatedAt }));
        return result({ ok: true, issues });
      } catch (error) { return failure(error); }
    },
  });
}
