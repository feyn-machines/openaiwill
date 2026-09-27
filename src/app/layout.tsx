import { LanguageSwitch } from "@/components/language-switch";
import { bilingual, getLocale } from "@/lib/i18n";
import type { Metadata } from "next";
import localFont from "next/font/local";
import Link from "next/link";
import "./globals.css";

const copy = bilingual({
  en: {
    metaDescription: "Every AI update could change your answer. Check your idea against what AI platforms already do and track what changes.",
    brandLabel: "openaiwill home",
    navLabel: "Main navigation",
    markets: "Markets",
    occupations: "Occupations",
    updates: "AI Updates",
    whitepaper: "Whitepaper",
    footerBrand: "openaiwill · Before you build.",
    footerNote: "Evidence first. Opinions that can change.",
  },
  "zh-CN": {
    metaDescription: "每一次 AI 更新，都可能改变你的创业判断。对照 AI 平台已经做到的事情检查你的想法，并跟踪它的变化。",
    brandLabel: "openaiwill 首页",
    navLabel: "主导航",
    markets: "赛道",
    occupations: "职业",
    updates: "AI 更新",
    whitepaper: "白皮书",
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
  src: "../../design/system-v1/fonts/InterTight-Variable.ttf",
  weight: "100 900",
  display: "swap",
  variable: "--font-display",
  fallback: ["PingFang SC", "Microsoft YaHei", "system-ui", "sans-serif"],
});

const jetBrainsMono = localFont({
  src: "../../design/system-v1/fonts/JetBrainsMono-Variable.ttf",
  weight: "100 800",
  display: "swap",
  variable: "--font-mono",
  fallback: ["SFMono-Regular", "Consolas", "monospace"],
});

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
  return (
    <html lang={language} className={`${interTight.variable} ${jetBrainsMono.variable}`}>
      <body>
        <header className="header wrap">
          <Link href="/" className="brand" aria-label={c.brandLabel}>openai<span>will</span><span className="brand-dot">.</span></Link>
          <div className="header-end">
            <nav aria-label={c.navLabel}><Link href="/markets">{c.markets}</Link><Link href="/occupations">{c.occupations}</Link><Link href="/updates">{c.updates}</Link><Link href="/whitepaper">{c.whitepaper}</Link></nav>
            <LanguageSwitch />
          </div>
        </header>
        <main className="wrap">{children}</main>
        <footer className="footer wrap"><span>{c.footerBrand}</span><span>{c.footerNote}</span></footer>
      </body>
    </html>
  );
}
