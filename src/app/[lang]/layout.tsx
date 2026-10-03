import { LanguageSwitch } from "@/components/language-switch";
import { LANGUAGES, bilingual } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";
import { SITE_NAV, siteNavCopy } from "@/lib/site-nav";
import type { Metadata } from "next";
import localFont from "next/font/local";
import Link from "next/link";
import "../globals.css";
import { href } from "@/lib/routes";

const copy = bilingual({
  en: {
    metaDescription: "Every AI update could change your answer. Check your idea against what AI platforms already do and track what changes.",
    brandLabel: "openaiwill home",
    footerBrand: "openaiwill · Before you build.",
    footerNote: "Evidence first. Opinions that can change.",
  },
  "zh-CN": {
    metaDescription: "每一次 AI 更新，都可能改变你的创业判断。对照 AI 平台已经做到的事情检查你的想法，并跟踪它的变化。",
    brandLabel: "openaiwill 首页",
    footerBrand: "openaiwill · 在动手之前。",
    footerNote: "以证据为先，判断随事实更新。",
  },
});

/**
 * The design system ships these two variable faces with their OFL licences, and
 * until now nothing loaded them: `--ah-font-display` named "AH Inter Tight", no
 * @font-face ever declared it, and every page fell through to Arial. next/font
 * self-hosts them and hands back the family name to bind the tokens to.
 */
const interTight = localFont({
  src: "../../../design/system-v1/fonts/InterTight-Variable.ttf",
  weight: "100 900",
  display: "swap",
  variable: "--font-display",
  fallback: ["PingFang SC", "Microsoft YaHei", "system-ui", "sans-serif"],
});

// The geometric face for the wordmark and the large headlines (brand type direction 02).
const outfit = localFont({
  src: "../../../design/system-v1/fonts/Outfit-Variable.ttf",
  weight: "100 900",
  display: "swap",
  variable: "--font-heading",
  fallback: ["PingFang SC", "Microsoft YaHei", "system-ui", "sans-serif"],
});

const jetBrainsMono = localFont({
  src: "../../../design/system-v1/fonts/JetBrainsMono-Variable.ttf",
  weight: "100 800",
  display: "swap",
  variable: "--font-mono",
  fallback: ["SFMono-Regular", "Consolas", "monospace"],
});

/** Both languages are built ahead of time; no other value of the segment is a page. */
export function generateStaticParams() {
  return LANGUAGES.map((lang) => ({ lang }));
}
export const dynamicParams = false;

/**
 * Static metadata cannot see the reader's language, so a Chinese reader was
 * getting an English <title> and description on every route that does not
 * define its own. The headline itself stays English in both - it is the
 * confirmed brand line - while the description and the tab suffix follow the
 * reader.
 */
export async function generateMetadata(): Promise<Metadata> {
  const { language } = await getLocale();
  return {
    title: { default: "Will AI Kill Your Idea?", template: "%s | openaiwill" },
    description: copy[language].metaDescription,
  };
}

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const { language } = await getLocale();
  const c = copy[language];
  const nav = siteNavCopy[language];
  return (
    <html lang={language} className={`${interTight.variable} ${outfit.variable} ${jetBrainsMono.variable}`}>
      <body>
        <header className="header wrap">
          <Link href={href(language, "/")} className="brand" aria-label={c.brandLabel}>open<span className="brand-ai">ai</span><span className="brand-will">will</span></Link>
          <div className="header-end">
            <nav aria-label={nav.navLabel}>{SITE_NAV.map((item) => <Link key={item.href} href={href(language, item.href)}>{nav[item.key]}</Link>)}</nav>
            <LanguageSwitch />
          </div>
        </header>
        <main className="wrap">{children}</main>
        <footer className="footer wrap"><span>{c.footerBrand}</span><span>{c.footerNote}</span></footer>
      </body>
    </html>
  );
}
