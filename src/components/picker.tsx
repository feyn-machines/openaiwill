"use client";

import { useEffect, useId, useRef, useState } from "react";
import s from "./picker.module.css";

/**
 * A single-choice menu drawn by the page, so the list of options looks like
 * the rest of the site instead of the operating system's menu. A button shows
 * the current choice; the list opens under it. Arrow keys move, Enter or Space
 * chooses, Escape closes, and a click anywhere else closes.
 */
export function Picker({ label, value, options, onChange }: {
  label: string;
  value: string;
  options: { value: string; label: string; note?: string }[];
  onChange: (value: string) => void;
}) {
  const id = useId();
  const root = useRef<HTMLDivElement>(null);
  const list = useRef<HTMLUListElement>(null);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const current = Math.max(0, options.findIndex((o) => o.value === value));

  useEffect(() => {
    if (!open) return;
    const away = (event: PointerEvent) => { if (!root.current?.contains(event.target as Node)) setOpen(false); };
    document.addEventListener("pointerdown", away);
    return () => document.removeEventListener("pointerdown", away);
  }, [open]);

  useEffect(() => {
    if (open) list.current?.children[active]?.scrollIntoView({ block: "nearest" });
  }, [open, active]);

  const choose = (index: number) => { onChange(options[index].value); setOpen(false); };
  const show = () => { setActive(current); setOpen(true); };
  const onKey = (event: React.KeyboardEvent) => {
    if (!open) {
      if (event.key === "ArrowDown" || event.key === "Enter" || event.key === " ") { event.preventDefault(); show(); }
      return;
    }
    if (event.key === "Escape") { event.preventDefault(); setOpen(false); }
    else if (event.key === "ArrowDown") { event.preventDefault(); setActive((i) => Math.min(options.length - 1, i + 1)); }
    else if (event.key === "ArrowUp") { event.preventDefault(); setActive((i) => Math.max(0, i - 1)); }
    else if (event.key === "Home") { event.preventDefault(); setActive(0); }
    else if (event.key === "End") { event.preventDefault(); setActive(options.length - 1); }
    else if (event.key === "Enter" || event.key === " ") { event.preventDefault(); choose(active); }
    else if (event.key === "Tab") setOpen(false);
  };

  return (
    <div ref={root} className={s.picker}>
      <span id={`${id}-label`} className={s.label}>{label}</span>
      <button
        type="button"
        className={`${s.button} ${open ? s.open : ""}`}
        role="combobox"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={`${id}-list`}
        aria-labelledby={`${id}-label ${id}-value`}
        aria-activedescendant={open ? `${id}-${active}` : undefined}
        onClick={() => (open ? setOpen(false) : show())}
        onKeyDown={onKey}
      >
        <span id={`${id}-value`}>{options[current]?.label}</span>
        <i aria-hidden="true" />
      </button>
      {open && (
        <ul ref={list} id={`${id}-list`} className={s.list} role="listbox" aria-labelledby={`${id}-label`}>
          {options.map((option, index) => (
            <li
              key={option.value}
              id={`${id}-${index}`}
              role="option"
              aria-selected={index === current}
              className={`${s.option} ${index === active ? s.active : ""} ${index === current ? s.current : ""}`}
              onPointerEnter={() => setActive(index)}
              onClick={() => choose(index)}
            >
              <span>{option.label}</span>
              {option.note ? <small>{option.note}</small> : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
