import { getLocale } from "@/lib/i18n";
import Link from "next/link";

export default async function Home() {
  const { t } = await getLocale();
  return (
    <>
      <section className="hero">
        <p className="eyebrow"><span className="dot" />{t("THE REALITY CHECK FOR YOUR NEXT IDEA")}</p>
        <h1>Will AI Kill<br />Your <em>Idea?</em></h1>
        <p className="lead">{t("Every AI update could change your answer.")}</p>
        <div className="actions"><Link className="button" href="/check">{t("Check your idea")}<span>↗</span></Link><Link className="text-link" href="/updates">{t("Explore AI updates →")}</Link></div>
        <p className="small">{t("For founders who would rather find out before they build.")}</p>
      </section>
      <section className="overview" aria-labelledby="how-it-works">
        <div className="section-heading"><p className="eyebrow">{t("FROM ANNOUNCEMENT TO IMPACT")}</p><h2 id="how-it-works">{t("A new feature.")}<br />{t("A different answer.")}</h2></div>
        <div className="steps">
          <article><span className="number">{t("01 / CHECK")}</span><h3>{t("Start with your idea.")}</h3><p>{t("Define who it serves, what it does, and why someone would pay.")}</p></article>
          <article><span className="number">{t("02 / COMPARE")}</span><h3>{t("Look at the evidence.")}</h3><p>{t("Compare the core promise with what AI platforms already ship.")}</p></article>
          <article><span className="number">{t("03 / TRACK")}</span><h3>{t("Know when things change.")}</h3><p>{t("Follow the releases that could weaken your reason to exist.")}</p></article>
        </div>
      </section>
      <aside className="notice"><span className="eyebrow">{t("EARLY DEVELOPMENT")}</span><p>{t("The idea checker and update feed are being built. No live assessments are available yet.")}</p></aside>
    </>
  );
}
