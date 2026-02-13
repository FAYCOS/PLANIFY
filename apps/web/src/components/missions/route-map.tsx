"use client";

import { useEffect } from "react";
import type { LatLngExpression } from "leaflet";
import dynamic from "next/dynamic";

const MapContainer = dynamic(
  () => import("react-leaflet").then((mod) => mod.MapContainer),
  { ssr: false },
);
const TileLayer = dynamic(
  () => import("react-leaflet").then((mod) => mod.TileLayer),
  { ssr: false },
);
const Marker = dynamic(
  () => import("react-leaflet").then((mod) => mod.Marker),
  { ssr: false },
);
const Polyline = dynamic(
  () => import("react-leaflet").then((mod) => mod.Polyline),
  { ssr: false },
);

type RouteMapProps = {
  origin?: LatLngExpression;
  destination?: LatLngExpression;
  geometry?: Array<[number, number]> | null;
};

const markerIcon =
  "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png";
const markerShadow =
  "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png";
const markerIcon2x =
  "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png";

export default function RouteMap({ origin, destination, geometry }: RouteMapProps) {
  useEffect(() => {
    let mounted = true;
    void (async () => {
      const L = await import("leaflet");
      if (!mounted) return;
      L.Icon.Default.mergeOptions({
        iconUrl: markerIcon,
        iconRetinaUrl: markerIcon2x,
        shadowUrl: markerShadow,
      });
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const center =
    (destination as LatLngExpression | undefined) ??
    (origin as LatLngExpression | undefined) ??
    ([46.603354, 1.888334] as LatLngExpression);

  return (
    <div className="h-72 w-full overflow-hidden rounded-xl border bg-white">
      <MapContainer
        center={center}
        zoom={12}
        scrollWheelZoom={false}
        className="h-full w-full"
      >
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {origin ? <Marker position={origin} /> : null}
        {destination ? <Marker position={destination} /> : null}
        {geometry && geometry.length > 1 ? (
          <Polyline positions={geometry} color="#1F7A5B" weight={4} />
        ) : null}
      </MapContainer>
    </div>
  );
}
