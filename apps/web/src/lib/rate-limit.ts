type RateLimitState = {
  count: number;
  reset: number;
};

const store = new Map<string, RateLimitState>();

export function rateLimit(key: string, limit: number, windowMs: number) {
  const now = Date.now();
  const current = store.get(key);
  if (!current || current.reset < now) {
    const reset = now + windowMs;
    store.set(key, { count: 1, reset });
    return { allowed: true, remaining: limit - 1, reset };
  }
  if (current.count >= limit) {
    return { allowed: false, remaining: 0, reset: current.reset };
  }
  current.count += 1;
  store.set(key, current);
  return { allowed: true, remaining: limit - current.count, reset: current.reset };
}

export function getRequestIp(req: Request) {
  const header = req.headers.get("x-forwarded-for") || "";
  const ip = header.split(",")[0]?.trim();
  return ip || req.headers.get("x-real-ip") || "unknown";
}
