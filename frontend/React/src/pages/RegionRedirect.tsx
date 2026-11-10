import { Navigate, useParams, useSearchParams } from "react-router";
import { href } from "@/content/url";

/** Old guide links (/regions/:id) now open the guide in the sheet over the map. */
export function RegionRedirect() {
  const { regionId } = useParams();
  const [searchParams] = useSearchParams();
  const { lang, tab, rule } = Object.fromEntries(searchParams);
  const target = rule
    ? { lang, tab, spot: rule, sheet: "full" }
    : { lang, tab, region: regionId, sheet: "full" };
  return <Navigate replace to={href("/", target)} />;
}
