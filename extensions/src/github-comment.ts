import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { failure, gh, requiredEnv, result } from "./shared.js";

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "github_comment",
    label: "GitHub comment",
    description: "Post a protocol-compliant comment on the current issue or a PR.",
    parameters: Type.Object({
      body: Type.String({ minLength: 1 }),
      target: Type.Optional(Type.Object({
        kind: Type.Union([Type.Literal("issue"), Type.Literal("pr")]),
        number: Type.Integer({ minimum: 1 }),
      })),
    }),
    async execute(_id, params, signal) {
      try {
        const repo = requiredEnv("GITHUB_REPO");
        const issue = Number(requiredEnv("GITHUB_ISSUE_NUMBER"));
        const username = requiredEnv("GITHUB_USERNAME");
        const target = params.target ?? { kind: "issue" as const, number: issue };
        if (target.kind === "issue") {
          const prefix = /^\[githubro:agent\]\[outcome:(success|clarification|audit-passed)\]/;
          if (!prefix.test(params.body)) throw new Error("issue comments must begin with a valid githubro outcome marker");
          if (!params.body.trimEnd().endsWith(`@${username}`)) throw new Error(`issue comments must end with @${username}`);
        }
        const command = target.kind === "issue" ? "issue" : "pr";
        const url = await gh([command, "comment", String(target.number), "--repo", repo, "--body", params.body], signal);
        const match = url.match(/#issuecomment-(\d+)/);
        return result({ ok: true, comment_id: match ? Number(match[1]) : null, url });
      } catch (error) { return failure(error); }
    },
  });
}
