import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { failure, gh, requiredEnv, result } from "./shared.js";

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "github_list_pr_comments", label: "List PR comments",
    description: "List issue-style and inline review comments for a PR.",
    parameters: Type.Object({ pr_number: Type.Integer({ minimum: 1 }) }),
    async execute(_id, params, signal) {
      try {
        const repo = requiredEnv("GITHUB_REPO");
        const [issueRaw, reviewRaw] = await Promise.all([
          gh(["api", `repos/${repo}/issues/${params.pr_number}/comments`], signal),
          gh(["api", `repos/${repo}/pulls/${params.pr_number}/comments`], signal),
        ]);
        return result({ ok: true, issue_comments: JSON.parse(issueRaw || "[]"), review_comments: JSON.parse(reviewRaw || "[]") });
      } catch (error) { return failure(error); }
    },
  });
}
