import type { Metadata } from "next";
import { bilingual } from "@/lib/i18n";
import { legalCopy } from "@/lib/legal";
import { getLocale } from "@/lib/locale";
import { pageMetadata } from "@/lib/seo";
import { LegalDoc } from "../legal-doc";

/** No data is read here, so like the whitepaper it is rendered at build time. */
export const dynamic = "force-static";

const meta = bilingual({
  en: { description: "What openaiwill stores about people who sign in, submit an account or subscribe, and how to have it deleted." },
  "zh-CN": { description: "openaiwill 对登录、提交帐号或订阅的人存储哪些信息，以及如何删除。" },
});

export async function generateMetadata(): Promise<Metadata> {
  const { language } = await getLocale();
  return pageMetadata({
    language,
    path: "/privacy",
    title: legalCopy[language].privacy.title,
    description: meta[language].description,
  });
}

export default async function PrivacyPage() {
  const { language } = await getLocale();
  return <LegalDoc doc={legalCopy[language].privacy} language={language} />;
}
