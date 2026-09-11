import { headers } from "next/headers";

const zh: Record<string, string> = {
  "AI Updates": "AI 更新",
  "Check your idea ↗": "检查你的想法 ↗",
  "WillAI · Before you build.": "AgentHowTo · 在动手之前。",
  "Evidence first. Opinions that can change.": "以证据为先，判断随事实更新。",
  "THE REALITY CHECK FOR YOUR NEXT IDEA": "看清 AI 对你的想法意味着什么",
  "Every AI update could change your answer.": "每一次 AI 更新，都可能改变你的创业判断。",
  "Check your idea": "检查你的想法",
  "Explore AI updates →": "查看 AI 更新 →",
  "For founders who would rather find out before they build.": "在投入之前，先了解 AI 已经覆盖了什么。",
  "FROM ANNOUNCEMENT TO IMPACT": "从官方发布到商业影响",
  "A new feature.": "一个新功能。",
  "A different answer.": "一个不同的判断。",
  "01 / CHECK": "01 / 检查",
  "Start with your idea.": "从你的想法出发。",
  "Define who it serves, what it does, and why someone would pay.": "明确服务谁、解决什么问题，以及用户为什么愿意付费。",
  "02 / COMPARE": "02 / 对比",
  "Look at the evidence.": "查看实际证据。",
  "Compare the core promise with what AI platforms already ship.": "将核心卖点与 AI 平台已经提供的功能进行对比。",
  "03 / TRACK": "03 / 追踪",
  "Know when things change.": "了解最新变化。",
  "Follow the releases that could weaken your reason to exist.": "追踪可能削弱产品独立价值的更新。",
  "EARLY DEVELOPMENT": "开发中",
  "The idea checker and update feed are being built. No live assessments are available yet.": "想法检查和更新列表仍在开发中，暂未提供实时评估。",
  "CHECK YOUR IDEA · COMING SOON": "检查你的想法 · 即将推出",
  "Before you": "在你",
  "build.": "动手之前。",
  "What would make someone pay for your idea when AI can already do part of the job?": "当 AI 已经能够完成部分工作时，用户为什么还愿意为你的想法付费？",
  "The questions we’ll start with": "先从这些问题开始",
  "Who is your customer?": "你的客户是谁？",
  "What specific task will your product complete?": "你的产品具体完成什么任务？",
  "Why would they choose it over a general AI platform?": "用户为什么选择它，而不是通用 AI 平台？",
  "The analysis service is not connected yet. Idea submission will be available in a future release.": "分析服务尚未接入，后续版本将开放想法提交。",
  "THE CHANGING LANDSCAPE": "持续变化的商业版图",
  "AI moves.": "AI 在前进。",
  "Ideas shift.": "判断也在变化。",
  "Official updates, connected to the ideas they could affect.": "连接官方更新与可能受到影响的创业方向。",
  "FEED STATUS / NOT CONNECTED": "更新状态 / 尚未接入",
  "Evidence is on the way.": "正在准备证据。",
  "There are no verified updates in the feed yet. Each entry will link to its official source and separate the announcement from our assessment.": "目前尚无已核实的更新。每条内容都会附上官方来源，并区分发布事实与本站判断。",
  "What shipped": "发布了什么",
  "What it replaces": "覆盖哪些任务",
  "Which ideas are affected": "影响哪些想法",
  "Check your idea →": "检查你的想法 →"
};

export function preferredLanguage(value: string | null): "en" | "zh-CN" {
  const preferences = (value ?? "").split(",").map((entry) => {
    const [tag, ...params] = entry.trim().toLowerCase().split(";");
    const q = params.find((p) => p.trim().startsWith("q="));
    return { tag, quality: q ? Number(q.trim().slice(2)) : 1 };
  }).filter(({ quality }) => Number.isFinite(quality) && quality > 0 && quality <= 1)
    .sort((a, b) => b.quality - a.quality);
  for (const { tag } of preferences) {
    if (/^zh(?:-|$)/.test(tag)) return "zh-CN";
    if (/^en(?:-|$)/.test(tag) || tag === "*") return "en";
  }
  return "en";
}

export async function getLocale() {
  const language = preferredLanguage((await headers()).get("accept-language"));
  return { language, t: (text: string) => language === "zh-CN" ? (zh[text] ?? text) : text };
}
