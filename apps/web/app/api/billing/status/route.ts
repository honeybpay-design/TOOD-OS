import { proxyToApi } from "@/lib/api-proxy";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  return proxyToApi("billing/status", request, "session");
}
