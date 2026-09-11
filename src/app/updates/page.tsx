import { getLocale } from "@/lib/i18n";
import type { Metadata } from "next";
import Link from "next/link";
export const metadata: Metadata = { title: "AI Updates", description: "Track AI platform updates and how they change the outlook for startup ideas." };
export default async function UpdatesPage() {
  const { t } = await getLocale();
  return <section className="inner-page"><p className="eyebrow">{t("THE CHANGING LANDSCAPE")}</p><h1>{t("AI moves.")}<br /><em>{t("Ideas shift.")}</em></h1><p className="lead">{t("Official updates, connected to the ideas they could affect.")}</p><div className="panel"><span className="number">{t("FEED STATUS / NOT CONNECTED")}</span><h2>{t("Evidence is on the way.")}</h2><p>{t("There are no verified updates in the feed yet. Each entry will link to its official source and separate the announcement from our assessment.")}</p><div className="tags"><span>{t("What shipped")}</span><span>{t("What it replaces")}</span><span>{t("Which ideas are affected")}</span></div></div><Link href="/check" className="text-link">{t("Check your idea →")}</Link></section>;
}
