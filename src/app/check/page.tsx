import { getLocale } from "@/lib/i18n";
import type { Metadata } from "next";
import Link from "next/link";
export const metadata: Metadata = { title: "Check Your Idea" };
export default async function CheckPage() {
  const { t } = await getLocale();
  return <section className="inner-page"><p className="eyebrow">{t("CHECK YOUR IDEA · COMING SOON")}</p><h1>{t("Before you")}<br /><em>{t("build.")}</em></h1><p className="lead">{t("What would make someone pay for your idea when AI can already do part of the job?")}</p><div className="panel"><h2>{t("The questions we’ll start with")}</h2><ol><li>{t("Who is your customer?")}</li><li>{t("What specific task will your product complete?")}</li><li>{t("Why would they choose it over a general AI platform?")}</li></ol><p className="muted">{t("The analysis service is not connected yet. Idea submission will be available in a future release.")}</p></div><Link href="/updates" className="text-link">{t("Explore AI updates →")}</Link></section>;
}
