const paths = {
  search: (
    <>
      <circle cx="11" cy="11" r="6.5" />
      <path d="m16 16 4.5 4.5" />
    </>
  ),
  locate: (
    <>
      <circle cx="12" cy="12" r="6.5" />
      <circle cx="12" cy="12" r="1.5" fill="currentColor" />
      <path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3" />
    </>
  ),
  locateOff: (
    <>
      <path d="M7.5 7.6A6.5 6.5 0 0 0 16.4 16.5M10 5.8a6.5 6.5 0 0 1 8.2 8.2" />
      <path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M4 4l16 16" />
    </>
  ),
  close: <path d="m6 6 12 12M18 6 6 18" />,
  arrow: <path d="M5 12h14M13 6l6 6-6 6" />,
  back: <path d="M19 12H5M11 6l-6 6 6 6" />,
  arrowUpRight: <path d="M7 17 17 7M9 7h8v8" />,
  pin: (
    <>
      <path d="M12 21s-6.5-6.2-6.5-11a6.5 6.5 0 0 1 13 0c0 4.8-6.5 11-6.5 11z" />
      <circle cx="12" cy="10" r="2.3" />
    </>
  ),
  explore: (
    <>
      <path d="M3 6.5 9 4l6 2.5L21 4v13.5L15 20l-6-2.5L3 20z" />
      <path d="M9 4v13.5M15 6.5V20" />
    </>
  ),
  residents: (
    <>
      <path d="M4 11.5 12 5l8 6.5" />
      <path d="M6.5 10v9.5h11V10" />
      <path d="M10 19.5v-5h4v5" />
    </>
  ),
  sign: (
    <>
      <rect x="4" y="4" width="16" height="10" rx="2" />
      <path d="M8 9h8M12 14v7M8.5 21h7" />
    </>
  ),
  bus: (
    <>
      <rect x="5" y="3.5" width="14" height="14" rx="3" />
      <path d="M5 11h14M8.5 17.5V20M15.5 17.5V20" />
      <circle cx="8.5" cy="14.2" r="0.9" fill="currentColor" />
      <circle cx="15.5" cy="14.2" r="0.9" fill="currentColor" />
    </>
  ),
  shop: (
    <>
      <path d="M4 9.5 5.5 4h13L20 9.5" />
      <path d="M4 9.5a2.7 2.7 0 0 0 5.3 0 2.7 2.7 0 0 0 5.4 0 2.7 2.7 0 0 0 5.3 0" />
      <path d="M5.5 12v8h13v-8M10 20v-5h4v5" />
    </>
  ),
};

export type IconName = keyof typeof paths;

type Props = { name: IconName; size?: number; strokeWidth?: number };

export function Icon({ name, size = 24, strokeWidth = 2 }: Props) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name]}
    </svg>
  );
}
