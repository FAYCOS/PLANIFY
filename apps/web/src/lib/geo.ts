import { db } from "@/db";
import { parametresEntreprise } from "@/db/schema";
import { eq } from "drizzle-orm";

type GeoPoint = {
  lat: number;
  lng: number;
};

export type RouteResult = {
  origin: GeoPoint & { address: string };
  destination: GeoPoint & { address: string };
  distanceKm: number | null;
  durationMin: number | null;
  source: "google" | "osrm";
  geometry: Array<[number, number]> | null;
};

const GOOGLE_KEY = process.env.GOOGLE_MAPS_API_KEY;

const userAgentHeaders = {
  "User-Agent": "Planify/1.0 (dev)",
};

const toNumber = (value: unknown) => {
  if (typeof value === "number") return value;
  if (typeof value === "string") return Number.parseFloat(value);
  return NaN;
};

const decodePolyline = (encoded: string): Array<[number, number]> => {
  let index = 0;
  let lat = 0;
  let lng = 0;
  const coordinates: Array<[number, number]> = [];

  while (index < encoded.length) {
    let result = 0;
    let shift = 0;
    let byte: number;
    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);
    const deltaLat = result & 1 ? ~(result >> 1) : result >> 1;
    lat += deltaLat;

    result = 0;
    shift = 0;
    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);
    const deltaLng = result & 1 ? ~(result >> 1) : result >> 1;
    lng += deltaLng;

    coordinates.push([lat / 1e5, lng / 1e5]);
  }

  return coordinates;
};

const geocodeGoogle = async (address: string): Promise<GeoPoint | null> => {
  if (!GOOGLE_KEY) return null;
  const url = new URL("https://maps.googleapis.com/maps/api/geocode/json");
  url.searchParams.set("address", address);
  url.searchParams.set("key", GOOGLE_KEY);
  const res = await fetch(url.toString());
  if (!res.ok) return null;
  const data = await res.json();
  const location = data?.results?.[0]?.geometry?.location;
  if (!location) return null;
  return { lat: location.lat, lng: location.lng };
};

const geocodeNominatim = async (address: string): Promise<GeoPoint | null> => {
  const url = new URL("https://nominatim.openstreetmap.org/search");
  url.searchParams.set("format", "json");
  url.searchParams.set("q", address);
  const res = await fetch(url.toString(), { headers: userAgentHeaders });
  if (!res.ok) return null;
  const data = await res.json();
  const first = data?.[0];
  if (!first) return null;
  return {
    lat: toNumber(first.lat),
    lng: toNumber(first.lon),
  };
};

const routeGoogle = async (
  origin: string,
  destination: string,
): Promise<RouteResult | null> => {
  if (!GOOGLE_KEY) return null;
  const url = new URL("https://maps.googleapis.com/maps/api/directions/json");
  url.searchParams.set("origin", origin);
  url.searchParams.set("destination", destination);
  url.searchParams.set("key", GOOGLE_KEY);
  const res = await fetch(url.toString());
  if (!res.ok) return null;
  const data = await res.json();
  const leg = data?.routes?.[0]?.legs?.[0];
  if (!leg) return null;
  const overview = data?.routes?.[0]?.overview_polyline?.points;
  const geometry = overview ? decodePolyline(overview) : null;
  return {
    origin: { lat: leg.start_location.lat, lng: leg.start_location.lng, address: origin },
    destination: {
      lat: leg.end_location.lat,
      lng: leg.end_location.lng,
      address: destination,
    },
    distanceKm: leg.distance?.value ? leg.distance.value / 1000 : null,
    durationMin: leg.duration?.value ? leg.duration.value / 60 : null,
    source: "google",
    geometry,
  };
};

const routeOsrm = async (
  origin: GeoPoint,
  destination: GeoPoint,
  originAddress: string,
  destinationAddress: string,
): Promise<RouteResult | null> => {
  const url = new URL(
    `https://router.project-osrm.org/route/v1/driving/${origin.lng},${origin.lat};${destination.lng},${destination.lat}`,
  );
  url.searchParams.set("overview", "full");
  url.searchParams.set("geometries", "geojson");
  const res = await fetch(url.toString());
  if (!res.ok) return null;
  const data = await res.json();
  const route = data?.routes?.[0];
  if (!route) return null;
  const geometry = route.geometry?.coordinates
    ? route.geometry.coordinates.map(
        (point: [number, number]) => [point[1], point[0]] as [number, number],
      )
    : null;

  return {
    origin: { ...origin, address: originAddress },
    destination: { ...destination, address: destinationAddress },
    distanceKm: route.distance ? route.distance / 1000 : null,
    durationMin: route.duration ? route.duration / 60 : null,
    source: "osrm",
    geometry,
  };
};

export const getEntrepriseOrigin = async (
  orgId?: string | null,
  tenantDb = db,
): Promise<string | null> => {
  const base = tenantDb.select().from(parametresEntreprise);
  const [row] = orgId
    ? await base.where(eq(parametresEntreprise.orgId, orgId)).limit(1)
    : await base.limit(1);
  if (!row) return null;
  const parts = [row.adresse, row.codePostal, row.ville].filter(Boolean);
  if (!parts.length) return null;
  return parts.join(" ");
};

export const computeRoute = async (
  destination: string,
  orgId?: string | null,
  tenantDb = db,
): Promise<RouteResult | null> => {
  const originAddress = await getEntrepriseOrigin(orgId, tenantDb);
  if (!originAddress) return null;

  if (GOOGLE_KEY) {
    const googleRoute = await routeGoogle(originAddress, destination);
    if (googleRoute) return googleRoute;
  }

  const origin = (await geocodeNominatim(originAddress)) ?? null;
  const dest = (await geocodeNominatim(destination)) ?? null;
  if (!origin || !dest) return null;

  return routeOsrm(origin, dest, originAddress, destination);
};
