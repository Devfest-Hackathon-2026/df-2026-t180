import { useCallback, useEffect, useState } from "react";
import type { LatLng } from "@/content/types";

export type LocationStatus = "idle" | "locating" | "on" | "denied" | "unavailable";

/** Kept for the session so the map still shows the visitor after moving between screens. */
let last: { status: LocationStatus; position?: LatLng } = { status: "idle" };

/**
 * Demo location, for recordings and presentations: open the app with ?demo=1 and the location
 * button places the visitor at a fixed spot in central Sakai (near the city office, among the
 * sample pins) without asking for permission. It stays on for the browser tab; ?demo=0 or closing
 * the tab turns it off. Without it, the real Geolocation API is used.
 */
const DEMO_POSITION: LatLng = { lat: 34.5738, lng: 135.4795 };
const DEMO_KEY = "manabi-demo-location";

export function isDemoLocation() {
  try {
    const flag = new URLSearchParams(window.location.search).get("demo");
    if (flag === "1") sessionStorage.setItem(DEMO_KEY, "1");
    if (flag === "0") sessionStorage.removeItem(DEMO_KEY);
    return sessionStorage.getItem(DEMO_KEY) === "1";
  } catch {
    return new URLSearchParams(window.location.search).get("demo") === "1";
  }
}

const options: PositionOptions = { enableHighAccuracy: true, timeout: 10000, maximumAge: 30000 };
const toLatLng = (p: GeolocationPosition): LatLng => ({
  lat: p.coords.latitude,
  lng: p.coords.longitude,
});

/**
 * The visitor's location, from the browser's Geolocation API. Nothing leaves the device: the
 * position is only used to draw the visitor on the map. Asks for permission on the first tap.
 */
export function useMyLocation() {
  const [status, setStatus] = useState<LocationStatus>(last.status);
  const [position, setPosition] = useState<LatLng | undefined>(last.position);
  /** Time of the latest request to move the map to the visitor (0 before any). */
  const [focus, setFocus] = useState(0);

  useEffect(() => {
    last = { status, position };
  }, [status, position]);

  // While location is on, keep the visitor's marker following them.
  useEffect(() => {
    if (status !== "on" || isDemoLocation() || !("geolocation" in navigator)) return;
    const id = navigator.geolocation.watchPosition(
      (p) => setPosition(toLatLng(p)),
      () => undefined,
      options,
    );
    return () => navigator.geolocation.clearWatch(id);
  }, [status]);

  const locate = useCallback(() => {
    if (isDemoLocation()) {
      // Same sequence as the real thing (searching, then found), at the demo spot.
      setStatus("locating");
      window.setTimeout(() => {
        setPosition(DEMO_POSITION);
        setStatus("on");
        setFocus(Date.now());
      }, 700);
      return;
    }
    if (!("geolocation" in navigator)) {
      setStatus("unavailable");
      return;
    }
    setStatus((current) => (current === "on" ? "on" : "locating"));
    navigator.geolocation.getCurrentPosition(
      (p) => {
        setPosition(toLatLng(p));
        setStatus("on");
        setFocus(Date.now());
      },
      (error) => setStatus(error.code === error.PERMISSION_DENIED ? "denied" : "unavailable"),
      options,
    );
  }, []);

  /** Turns location off: forgets the position and stops following. The map stays where it is. */
  const stop = useCallback(() => {
    setStatus("idle");
    setPosition(undefined);
  }, []);

  /** Moves the map back to the visitor without asking for the position again. */
  const recenter = useCallback(() => setFocus(Date.now()), []);

  /**
   * The location button. Off: find the visitor. On and the map shows them: turn off. On but the
   * map has moved elsewhere (back to the region, or panned away): fly back to them instead.
   */
  const toggle = useCallback(
    (showingMe = true) => {
      if (status !== "on") locate();
      else if (showingMe) stop();
      else recenter();
    },
    [status, stop, locate, recenter],
  );

  return { status, position, focus, locate, stop, recenter, toggle };
}

/** Distance in kilometres between two points. */
export function distanceKm(a: LatLng, b: LatLng) {
  const rad = (d: number) => (d * Math.PI) / 180;
  const dLat = rad(b.lat - a.lat);
  const dLng = rad(b.lng - a.lng);
  const h =
    Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 6371 * 2 * Math.asin(Math.sqrt(h));
}
