import {
  type CSSProperties,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { useNavigate } from "react-router";
import { categories, t } from "@/content/copy";
import type { Category, Lang, LatLng, PinnedRule, Region } from "@/content/types";
import type { Params } from "@/content/url";
import { CategoryIcon } from "./CategoryIcon";
import { GuideContent } from "./GuideContent";
import { Icon } from "./Icon";
import { Tag } from "./Tag";
import styles from "./PlaceSheet.module.css";

export type SheetMode = "half" | "full";

type Props = {
  mode: SheetMode;
  region: Region;
  rule?: PinnedRule;
  tab: Category;
  lang: Lang;
  linkTo: (patch: Params) => string;
  closeTo: string;
  expandTo: string;
  /** Where dragging down from full goes: back to the pin summary, or closed when there is none. */
  collapseTo: string;
  /** Controls that ride on top of the half sheet on phones, such as the location button. */
  above?: ReactNode;
  /** The visitor's position, used to sort place rules when no pin is open. */
  me?: LatLng;
};

type Target = "full" | "half" | "closed";

const desktop = () => window.matchMedia("(min-width: 900px)").matches;

/**
 * Map-first detail, as in Google Maps: a pin opens a half sheet over the map, dragging up (or the
 * arrow) expands it into the regional guide, dragging down or × returns to the map. No page change.
 */
export function PlaceSheet(props: Props) {
  const { mode, region, rule, tab, lang, linkTo, closeTo, expandTo, collapseTo, above, me } = props;
  const navigate = useNavigate();
  const sheetRef = useRef<HTMLElement>(null);
  const grabRef = useRef<HTMLDivElement>(null);
  const summaryRef = useRef<HTMLDivElement>(null);
  const scrollerRef = useRef<HTMLDivElement>(null);
  const drag = useRef<{ y: number; start: number; time: number; moved: boolean } | null>(null);
  const suppressClick = useRef(false);
  const [peek, setPeek] = useState(0);

  // Half height = handle and header plus the pin summary.
  useLayoutEffect(() => {
    const measure = () =>
      setPeek((grabRef.current?.offsetHeight ?? 0) + (summaryRef.current?.offsetHeight ?? 0) + 4);
    measure();
    const observer = new ResizeObserver(measure);
    if (grabRef.current) observer.observe(grabRef.current);
    if (summaryRef.current) observer.observe(summaryRef.current);
    return () => observer.disconnect();
  }, [rule?.id, lang]);

  // Back to the short card: the scroller keeps its scroll position even with overflow hidden, so
  // reset it, or guide rows (and their links) would show in place of the summary and arrow.
  useLayoutEffect(() => {
    if (mode === "half" && scrollerRef.current) scrollerRef.current.scrollTop = 0;
  }, [mode]);

  // Opening the full guide brings the tapped rule into view inside the sheet.
  useEffect(() => {
    const scroller = scrollerRef.current;
    if (mode !== "full" || !scroller) return;
    const focused = rule ? scroller.querySelector<HTMLElement>(`[id="${rule.id}"]`) : null;
    const bottom = focused ? focused.offsetTop + focused.offsetHeight : 0;
    // Only scroll when the rule would otherwise be hidden; keep the region intro in view if it fits.
    scroller.scrollTop =
      focused && bottom > scroller.clientHeight
        ? Math.max(0, focused.offsetTop - scroller.clientHeight / 3)
        : 0;
  }, [mode, rule, tab]);

  function settle(target: Target) {
    const sheet = sheetRef.current;
    const go = { full: expandTo, half: collapseTo, closed: closeTo }[target];
    if (!sheet || desktop()) {
      navigate(go, { preventScrollReset: true });
      return;
    }
    const height = sheet.offsetHeight;
    const y = { full: 0, half: height - peek, closed: height }[target];
    delete sheet.dataset.dragging;
    sheet.style.translate = `0 ${y}px`;
    let finished = false;
    const done = () => {
      if (finished) return;
      finished = true;
      sheet.style.translate = "";
      if (target === "closed") navigate(go, { preventScrollReset: true });
    };
    sheet.addEventListener("transitionend", done, { once: true });
    // Fallback for when no transition runs (already in place, or reduced motion).
    window.setTimeout(done, 450);
    if (target !== "closed") navigate(go, { preventScrollReset: true, replace: true });
  }

  function onPointerDown(event: ReactPointerEvent<HTMLElement>) {
    const sheet = sheetRef.current;
    const target = event.target as HTMLElement;
    if (!sheet || desktop() || event.button !== 0) return;
    if (target.closest("a, [data-nodrag]")) return;
    if (mode === "full" && !grabRef.current?.contains(target)) return;
    const translate = getComputedStyle(sheet).translate.split(" ")[1];
    const start = translate ? parseFloat(translate) : 0;
    drag.current = { y: event.clientY, start, time: performance.now(), moved: false };
    sheet.setPointerCapture(event.pointerId);
  }

  function onPointerMove(event: ReactPointerEvent<HTMLElement>) {
    const sheet = sheetRef.current;
    const state = drag.current;
    if (!sheet || !state) return;
    const delta = event.clientY - state.y;
    if (!state.moved && Math.abs(delta) < 6) return;
    state.moved = true;
    sheet.dataset.dragging = "";
    const y = Math.min(Math.max(state.start + delta, 0), sheet.offsetHeight);
    sheet.style.translate = `0 ${y}px`;
  }

  function onPointerUp(event: ReactPointerEvent<HTMLElement>) {
    const state = drag.current;
    drag.current = null;
    if (!state?.moved) return;
    suppressClick.current = true;
    const delta = event.clientY - state.y;
    const speed = delta / Math.max(1, performance.now() - state.time);
    const up = delta < -60 || speed < -0.5;
    const down = delta > 60 || speed > 0.5;
    if (mode === "half") settle(up ? "full" : down ? "closed" : "half");
    else settle(down ? (rule ? "half" : "closed") : "full");
  }

  function toggle() {
    if (suppressClick.current) {
      suppressClick.current = false;
      return;
    }
    settle(mode === "half" ? "full" : rule ? "half" : "closed");
  }

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") navigate(closeTo, { preventScrollReset: true });
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [closeTo, navigate]);

  // "Daisen Park, Sakai" / 「大仙公園・堺市」; just the area when the guide opens from search.
  const title = rule
    ? `${rule.place[lang]}${lang === "ja" ? "・" : ", "}${region.name[lang]}`
    : region.name[lang];

  return (
    <section
      ref={sheetRef}
      className={styles.sheet}
      data-mode={mode}
      aria-labelledby="sheet-title"
      style={{ "--peek": `${peek}px` } as CSSProperties}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
    >
      {above && <div className={styles.above}>{above}</div>}

      <div ref={grabRef} className={styles.grab}>
        <button
          type="button"
          className={styles.handle}
          onClick={toggle}
          aria-label={t(mode === "half" ? "openGuide" : "collapse", lang)}
          aria-expanded={mode === "full"}
        >
          <span aria-hidden="true" />
        </button>
        <div className={styles.head}>
          {rule ? (
            <Tag tone={rule.category} icon={<CategoryIcon category={rule.category} size={14} />}>
              {categories[rule.category].label[lang]}
            </Tag>
          ) : (
            <span />
          )}
          <button
            type="button"
            className={styles.close}
            onClick={() => settle("closed")}
            aria-label={t("close", lang)}
            data-nodrag
          >
            <Icon name="close" size={20} />
          </button>
        </div>
        <h2 className={styles.title} id="sheet-title">
          {title}
        </h2>
        <p className={styles.parent}>{region.parent[lang]}</p>
      </div>

      <div ref={scrollerRef} className={styles.scroller}>
        {rule && (
          <div ref={summaryRef} className={styles.summary}>
            <p className={styles.statement}>{rule.statement[lang]}</p>
            <button
              type="button"
              className={styles.open}
              onClick={() => settle("full")}
              aria-label={t("openGuide", lang)}
              data-nodrag
            >
              <Icon name="arrowUpRight" size={24} strokeWidth={2.4} />
            </button>
          </div>
        )}
        {/* In the short card only the arrow opens the guide; its content can't be tapped or focused. */}
        <div className={styles.guide} inert={mode === "half"}>
          <GuideContent
            region={region}
            lang={lang}
            tab={tab}
            focusedId={rule?.id}
            linkTo={linkTo}
            origin={rule?.location ?? me}
          />
        </div>
      </div>
    </section>
  );
}
