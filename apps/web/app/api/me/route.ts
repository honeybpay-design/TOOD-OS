import { proxyToApi } from "@/lib/api-proxy";

// Auth-dependent: always run at request time, never prerendered.
export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  return proxyToApi("me", request, "session");
}
