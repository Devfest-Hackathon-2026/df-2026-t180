import {
  AdvancedMarker,
  APILoadingStatus,
  APIProvider,
  Map,
  useApiLoadingStatus,
  useMap,
} from "@vis.gl/react-google-maps";
import { type CSSProperties, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { categories, t } from "@/content/copy";
import type { Category, Lang, LatLng } from "@/content/types";
import { MapMarker } from "./MapMarker";
import { Mascot } from "./Mascot";
import { MapPlaceholder } from "./MapPlaceholder";
import styles from "./MapView.module.css";

export type MapPin = {
  id: string;
  name: string;
  category: Category;
  location: LatLng;
  to: string;
};

type Props = {
  lang: Lang;
  center: LatLng;
  zoom: number;
  pins: MapPin[];
  selectedId?: string;
  dimmed?: boolean;
  loading?: boolean;
  /** Reports the map centre after it settles. Only the live map can do this. */
  onCenterChange?: (center: LatLng) => void;
  /** The visitor's own position, drawn as the mascot. */
  you?: LatLng;
  /** Moves the map whenever `key` changes, e.g. to the visitor or back to the region. */
  flyTo?: { center: LatLng; zoom?: number; key: number };
};

const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string | undefined;
const mapId = import.meta.env.VITE_GOOGLE_MAP_ID as string | undefined;

/**
 * The map. Uses the Google Maps JavaScript API when a key is set in .env, and falls back to the
 * static placeholder drawing without a key or if the key is rejected, so the app always runs.
 */
export function MapView(props: Props) {
  // The API loads once per page, so it keeps the language the visitor arrived with.
  const [language] = useState(props.lang);
  if (!apiKey) return <PlaceholderMap {...props} />;
  return (
    <APIProvider apiKey={apiKey} language={language} region="JP">
      <GoogleMap {...props} />
    </APIProvider>
  );
}

function GoogleMap(props: Props) {
  const { center, zoom, pins, selectedId, dimmed, loading, lang, onCenterChange, you, flyTo } =
    props;
  const status = useApiLoadingStatus();
  const navigate = useNavigate();
  const selected = pins.find((pin) => pin.id === selectedId);

  if (status === APILoadingStatus.AUTH_FAILURE || status === APILoadingStatus.FAILED) {
    return <PlaceholderMap {...props} />;
  }

  return (
    <div className={styles.region} data-loading={loading || undefined}>
      <Map
        className={styles.google}
        mapId={mapId}
        defaultCenter={center}
        defaultZoom={zoom}
        disableDefaultUI
        clickableIcons={false}
        gestureHandling="greedy"
        reuseMaps
        onIdle={(event) => {
          const centre = event.map.getCenter();
          if (centre && onCenterChange) onCenterChange(centre.toJSON());
        }}
      >
        {!loading &&
          pins.map((pin) => (
            <AdvancedMarker
              key={pin.id}
              position={pin.location}
              anchorPoint={["22px", "22px"]}
              zIndex={pin.id === selectedId ? 10 : 1}
              title={`${pin.name}, ${categories[pin.category].label[lang]}`}
              onClick={() => navigate(pin.to, { preventScrollReset: true })}
            >
              <MapMarker
                name={pin.name}
                category={pin.category}
                lang={lang}
                to={pin.to}
                selected={pin.id === selectedId}
                dimmed={dimmed}
                asContent
              />
            </AdvancedMarker>
          ))}
        {you && (
          <AdvancedMarker
            position={you}
            anchorPoint={[`${(60 / 140) * 100}%`, "100%"]}
            zIndex={30}
            title={t("youAreHere", lang)}
          >
            <span className={styles.you}>
              <span className={styles.halo} aria-hidden="true" />
              <Mascot className={styles.youMascot} size={64} />
            </span>
          </AdvancedMarker>
        )}
        <PanToSelected target={selected?.location} />
        <FlyTo target={flyTo} />
      </Map>
    </div>
  );
}

/** Centres the selected pin in one smooth movement. */
function PanToSelected({ target }: { target?: LatLng }) {
  const map = useMap();
  const lat = target?.lat;
  const lng = target?.lng;

  useEffect(() => {
    if (!map || lat === undefined || lng === undefined) return;
    map.panTo({ lat, lng });
  }, [map, lat, lng]);

  return null;
}

/** Moves the map to a requested place, once per request. */
function FlyTo({ target }: { target?: { center: LatLng; zoom?: number; key: number } }) {
  const map = useMap();
  const key = target?.key;
  const lastKey = useRef(0);
  useEffect(() => {
    if (!map || !target || target.key <= lastKey.current) return;
    lastKey.current = target.key;
    map.panTo(target.center);
    if (target.zoom) map.setZoom(target.zoom);
    // Only a new key should move the map; the target object itself changes on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, key]);
  return null;
}

/** Fallback: the static drawing, with pins projected from their real coordinates. */
function PlaceholderMap({ pins, selectedId, dimmed, loading, lang }: Props) {
  const lats = pins.map((pin) => pin.location.lat);
  const lngs = pins.map((pin) => pin.location.lng);
  const [minLat, maxLat, minLng, maxLng] = [
    Math.min(...lats),
    Math.max(...lats),
    Math.min(...lngs),
    Math.max(...lngs),
  ];
  const project = ({ lat, lng }: LatLng) => ({
    x: 30 + (40 * (lng - minLng)) / (maxLng - minLng || 1),
    y: 30 + (40 * (maxLat - lat)) / (maxLat - minLat || 1),
  });

  const selected = pins.find((pin) => pin.id === selectedId);
  const at = selected ? project(selected.location) : undefined;
  const canvasStyle = at
    ? ({ "--pan-x": `${50 - at.x}%`, "--pan-y": `${50 - at.y}%` } as CSSProperties)
    : undefined;

  return (
    <div className={styles.region} data-loading={loading || undefined}>
      <div className={styles.canvas} style={canvasStyle}>
        <MapPlaceholder />
        {!loading &&
          pins.map((pin) => (
            <MapMarker
              key={pin.id}
              name={pin.name}
              category={pin.category}
              lang={lang}
              to={pin.to}
              selected={pin.id === selectedId}
              dimmed={dimmed}
              position={project(pin.location)}
            />
          ))}
      </div>
    </div>
  );
}
