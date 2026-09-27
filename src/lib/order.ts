/**
 * Ordering that is identical on the server and in the browser.
 *
 * `String.prototype.localeCompare` is not: Node's ICU and Chrome's ICU disagree
 * about Chinese, so a list sorted with it renders in one order on the server and
 * another after hydration. React reports that as a text mismatch (error #418)
 * and throws away the server HTML for that subtree.
 *
 * It is not hypothetical here. The occupation directory's default sort is by
 * share, 747 of its 923 rows share the value 0, and the tie-break was the label —
 * so almost the whole page was ordered by a comparison the two sides did not
 * agree on.
 *
 * Use `byText` for any comparison that can run during the first render: a
 * default sort, or the tie-break inside one. A locale-aware sort a reader asks
 * for by clicking is fine, because by then hydration is done.
 *
 * This module opens no files and imports nothing, so client components may use
 * it freely.
 */

/** Code-point order. Same answer in every JavaScript engine, always. */
export function byText(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}
