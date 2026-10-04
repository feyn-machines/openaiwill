import { AccountMenu } from "@/components/account/account-menu";
import { Subscribe } from "@/components/account/subscribe";
import { LanguageSwitch } from "@/components/language-switch";
import { appEnabled } from "@/lib/app-config";
import { LANGUAGES, bilingual } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";
import { SITE_NAV, siteNavCopy } from "@/lib/site-nav";
import type { Metadata } from "next";
import localFont from "next/font/local";
import Link from "next/link";
import "../globals.css";
import { href } from "@/lib/routes";
import { SITE_NAME, SITE_URL, SOCIAL_LINKS, siteCopy } from "@/lib/seo";

const copy = bilingual({
  en: {
    brandLabel: "openaiwill home",
    footerBrand: "openaiwill · Before you build.",
    footerNote: "Evidence first. Opinions that can change.",
    socialLinks: "openaiwill elsewhere",
  },
  "zh-CN": {
    brandLabel: "openaiwill 首页",
    footerBrand: "openaiwill · 在动手之前。",
    footerNote: "以证据为先，判断随事实更新。",
    socialLinks: "openaiwill 的其他地址",
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

/** Both languages are the only values of the segment; any other one is a 404. */
export function generateStaticParams() {
  return LANGUAGES.map((lang) => ({ lang }));
}
export const dynamicParams = false;

/** Titles and descriptions follow the language of the address, not the reader's browser. */
export async function generateMetadata(): Promise<Metadata> {
  const { language } = await getLocale();
  return {
    metadataBase: new URL(SITE_URL),
    title: { default: siteCopy[language].title, template: `%s | ${SITE_NAME}` },
    description: siteCopy[language].description,
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
            <nav className="header-social" aria-label={c.socialLinks}>
              {SOCIAL_LINKS.map((link) => (
                <a key={link.href} href={link.href} rel="noopener">{link.label}</a>
              ))}
            </nav>
            <LanguageSwitch />
            <AccountMenu language={language} enabled={appEnabled()} />
          </div>
        </header>
        <main className="wrap">{children}</main>
        <footer className="footer wrap">
          <span>{c.footerBrand}</span>
          <span>{c.footerNote}</span>
          <Subscribe language={language} enabled={appEnabled()} />
          <div className="footer-links">
            {SOCIAL_LINKS.map((link) => (
              <a key={link.href} href={link.href} rel="noopener">{link.label}</a>
            ))}
          </div>
        </footer>
      </body>
    </html>
  );
}
