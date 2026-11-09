import { type MouseEvent, useEffect, useRef, useState } from "react";
import { type NavigateOptions, useNavigate } from "react-router";

/** Matches --duration-slow, the length of every pill thumb slide. */
const SLIDE_MS = 320;

/**
 * The bottom nav (探す / 地元の方) slides its thumb first and changes the page only once the slide
 * has finished. Other pill switches (JP / EN, 候補 / 公開ルール) change content straight away while
 * their thumb slides: they stay on the same screen, so there is no heavy page to build.
 *
 * Why: changing the route in the same moment as the slide makes the slide compete with whatever the
 * new screen has to build. The map screen is heavy (Google Maps and its pins), so its first frame
 * arrived after most of the slide had already elapsed and the thumb appeared to jump. Sliding on
 * the current, idle screen keeps it smooth everywhere, and the new screen simply draws the thumb in
 * its final place.
 */
export function useSlideNavigate<T>(current: T) {
  const navigate = useNavigate();
  // The option being switched to, and the value it is switching from. Held until the route actually
  // changes: React Router keeps the old screen up while it prepares the next one (the map takes a
  // moment), and letting go earlier made the thumb slide back for a few frames before the swap.
  const [pending, setPending] = useState<{ value: T; from: T }>();
  const timer = useRef<number>(undefined);
  const latest = useRef(current);

  useEffect(() => {
    latest.current = current;
  }, [current]);
  useEffect(() => () => window.clearTimeout(timer.current), []);

  // Once the route has moved on (to the target, or anywhere else such as via the back button), the
  // switch is over: forget it, so returning to the starting page later shows that page's option.
  if (pending && current !== pending.from) setPending(undefined);

  /**
   * Where the thumb should be drawn: the option being switched to while the switch is under way
   * (the route still shows where it came from), otherwise wherever the route now is.
   */
  const shown = pending && current === pending.from ? pending.value : current;

  function go(value: T, to: string, event?: MouseEvent, options?: NavigateOptions) {
    // Let the browser handle new-tab and new-window clicks as usual.
    if (event && (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey)) return;
    event?.preventDefault();
    if (value === shown) return;
    window.clearTimeout(timer.current);
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      navigate(to, options);
      return;
    }
    const from = current;
    setPending({ value, from });
    timer.current = window.setTimeout(() => {
      // Skip if the visitor went elsewhere mid-slide (e.g. the back button).
      if (latest.current === from) navigate(to, options);
    }, SLIDE_MS);
  }

  return { shown, go };
}
