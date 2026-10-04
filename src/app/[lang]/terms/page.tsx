import type { Metadata } from "next";
import { bilingual } from "@/lib/i18n";
import { legalCopy } from "@/lib/legal";
import { getLocale } from "@/lib/locale";
import { pageMetadata } from "@/lib/seo";
import { LegalDoc } from "../legal-doc";

/** No data is read here, so like the whitepaper it is rendered at build time. */
export const dynamic = "force-static";

const meta = bilingual({
  en: { description: "The terms for using openaiwill: the data is machine-proposed and unreviewed, and what to submit." },
  "zh-CN": { description: "使用 openaiwill 的条款：数据由机器提出、未经审核，以及可以提交什么。" },
});

export async function generateMetadata(): Promise<Metadata> {
  const { language } = await getLocale();
  return pageMetadata({
    language,
    path: "/terms",
    title: legalCopy[language].terms.title,
    description: meta[language].description,
  });
}

export default async function TermsPage() {
  const { language } = await getLocale();
  return <LegalDoc doc={legalCopy[language].terms} language={language} />;
}
