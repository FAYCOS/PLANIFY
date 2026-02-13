import Script from "next/script";

const plausibleDomain = process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN;
const posthogKey = process.env.NEXT_PUBLIC_POSTHOG_KEY;
const posthogHost = process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://app.posthog.com";
const posthogHostNormalized = posthogHost.replace(/\/$/, "");
const metaPixelId = process.env.NEXT_PUBLIC_META_PIXEL_ID;
const datafastKey = process.env.NEXT_PUBLIC_DATAFAST_KEY;
const datafastSrc = process.env.NEXT_PUBLIC_DATAFAST_SRC;

export function AnalyticsScripts() {
  return (
    <>
      {plausibleDomain ? (
        <Script
          defer
          data-domain={plausibleDomain}
          src="https://plausible.io/js/script.js"
        />
      ) : null}

      {posthogKey ? (
        <Script id="posthog-init" strategy="afterInteractive">
          {`
            !function(t,e){var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(i,s,a){function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}(p=t.createElement("script")).type="text/javascript",p.async=!0,p.src="${posthogHostNormalized}/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=function(t){var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+" (stub)"),e},u.people.toString=function(){return u.toString(1)+".people (stub)"},n="capture identify alias people.set people.set_once people.unset people.increment people.append people.remove people.group group_identify group_set group_unset group_remove group_set_once group_append group_increment reset on off".split(" "),o=0;o<n.length;o++)g(u,n[o]);e._i.push([i,s,a])},e.__SV=1)}(document,window.posthog||[]);
            posthog.init("${posthogKey}", {api_host: "${posthogHost}"});
          `}
        </Script>
      ) : null}

      {metaPixelId ? (
        <>
          <Script id="meta-pixel" strategy="afterInteractive">
            {`
              !function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?
              n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;
              n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;
              t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window, document,'script',
              'https://connect.facebook.net/en_US/fbevents.js');
              fbq('init', '${metaPixelId}');
              fbq('track', 'PageView');
            `}
          </Script>
          <noscript>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              height="1"
              width="1"
              style={{ display: "none" }}
              src={`https://www.facebook.com/tr?id=${metaPixelId}&ev=PageView&noscript=1`}
              alt=""
            />
          </noscript>
        </>
      ) : null}

      {datafastKey && datafastSrc ? (
        <Script
          id="datafast"
          data-key={datafastKey}
          src={datafastSrc}
          strategy="afterInteractive"
        />
      ) : null}
    </>
  );
}
