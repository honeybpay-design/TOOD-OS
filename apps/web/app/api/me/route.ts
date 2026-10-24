import { proxyToApi } from "@/lib/api-proxy";
import { cookies } from "next/headers";

// Auth-dependent: always run at request time, never prerendered.
export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const cookieStore = await cookies();
  const token = cookieStore.get("__session")?.value;
  console.log("[/api/me] __session cookie present:", !!token, "length:", token?.length ?? 0);
  return proxyToApi("me", request, "session");
}
