# TOOD-OS — Handover TODO
**Last updated:** 17 October 2026 — 07:40 GMT (London)
**Status:** Production partially live — OAuth login broken at dashboard step

---

## สถานะปัจจุบัน

### ✅ เสร็จแล้ว
- **tood.uk live** — Firebase Hosting + Cloud Run Web + API ทำงานได้
- **Landing page** — trial CTA, stats bar, how-it-works, pricing ถูกต้อง
- **Google OAuth** — login button → Google consent screen → callback ทำงาน (API return 302 พร้อม session_token)
- **Stripe** — webhook secret จริง (`whsec_vHpKIqbbXcTMxdQEuxZH1rB1WNV49yFK`), publishable key เป็น live key แล้ว
- **RLS migrations** — 0007 applied บน Cloud SQL แก้ subscriptions RLS bug แล้ว
- **API health** — 17/17 checks pass, 51/51 tests pass
- **Fake testimonial** — "Sarah Chen, NHS Trust" เอาออกจาก login page แล้ว
- **CORS** — เปิดแล้วใน FastAPI main.py สำหรับ tood.uk origins
- **CI/CD** — แก้ `hashFiles` invalid syntax ใน ci.yml แล้ว (run #21 ควรผ่าน)
- **GitHub main** — code ทั้งหมด push ขึ้น main แล้ว

---

## 🔴 ปัญหาที่ยังค้างอยู่ (BLOCKER)

### Dashboard ใช้งานไม่ได้ — session token ไม่ save

**อาการ:**
1. User login ด้วย Google → consent screen ขึ้น → callback สำเร็จ
2. Browser redirect มาที่ `/dashboard?session_token=XXX`
3. Dashboard เด้งกลับไปที่ `/login` ทันที
4. `sessionStorage.getItem("tood_session")` return `null`
5. `GET /v1/me` return 401

**Root cause ที่สงสัย:**
- Next.js API route ที่ `apps/web/app/auth/google/callback/route.ts` ควรรับ request และ save token ผ่าน HTML/JS ก่อน redirect
- แต่ Firebase Hosting อาจ bypass Next.js และส่ง `/auth/google/callback` ตรงไปที่ API Cloud Run แทน
- ทดสอบด้วย `curl https://tood.uk/auth/google/callback?code=test&state=test` ได้ `{"detail":"invalid state"}` จาก FastAPI โดยตรง — แปลว่า Next.js route ไม่ได้ถูกเรียกเลย

**สิ่งที่ลองแล้วไม่หาย:**
- แก้ next.config.ts rewrite หลายรอบ
- สร้าง Next.js API route (`route.ts`) ที่ proxy callback และ return HTML/JS เพื่อ save token
- เพิ่ม CORS middleware ใน FastAPI
- เปลี่ยน API URL จาก relative เป็น absolute และกลับมา relative
- อัพเดท `NEXT_PUBLIC_API_URL` env var (แต่เป็น build-time variable ต้อง rebuild)

**สิ่งที่ต้องทำต่อ:**

**Option A (แนะนำ):** เปลี่ยน callback flow ให้ใช้ cookie แทน sessionStorage
- API ส่ง session token กลับมาเป็น HttpOnly cookie แทน query param
- ไม่ต้องพึ่ง sessionStorage เลย
- แก้ที่ `apps/api/app/routes_oauth.py` บรรทัด `return RedirectResponse(url=f"https://tood.uk/dashboard?session_token={session_token}"...)`
- เปลี่ยนเป็น set cookie แล้ว redirect ไป `/dashboard` โดยตรง
- แก้ `apps/web/app/dashboard/page.tsx` ให้อ่าน token จาก cookie แทน sessionStorage

**Option B:** Fix Firebase routing ให้ `/auth/google/callback` ผ่าน Next.js จริงๆ
- ตรวจ `firebase.json` ว่า route `**` ส่งไปที่ `tood-os-web` (Next.js) จริง
- ปัญหาอาจเป็นว่า Next.js standalone mode ไม่ serve API routes ผ่าน Cloud Run

---

## 📋 Post-Launch Tasks (ไม่ urgent)

| Task | รายละเอียด |
|------|-----------|
| ย้าย Cloud SQL region | ตอนนี้อยู่ `us-east4` ควรย้ายไป `europe-west2` เพื่อ GDPR/UK data residency |
| Session token ใน URL | เปลี่ยนจาก query param เป็น HttpOnly cookie (OWASP CWE-598) |
| Malware scanning | ยังไม่มี AV scanner บน file upload |
| ALLOW_SIGNUP=false | ปิด open signup endpoint ใน production |
| admin_force_plan bug | ใช้ `database_url` แทน `database_admin_url` — UPDATE silently fails |
| Cloud SQL → europe-west2 | export/import data แล้วสร้าง instance ใหม่ |

---

## สถาปัตยกรรม

```
Browser → Firebase Hosting (tood.uk)
           ├── /v1/**          → Cloud Run: tood-os-api (FastAPI)
           ├── /healthz        → Cloud Run: tood-os-api
           ├── /auth/google/callback → Cloud Run: tood-os-web (Next.js) ← ปัญหาอยู่ตรงนี้
           └── **              → Cloud Run: tood-os-web (Next.js)

api.tood.uk → Firebase Hosting → Cloud Run: tood-os-api (ทุก route)
```

## URLs สำคัญ

| สิ่งที่ | URL |
|---------|-----|
| Production web | https://tood.uk |
| API (Cloud Run direct) | https://tood-os-api-iiwda4phia-nw.a.run.app |
| Web (Cloud Run direct) | https://tood-os-web-844874461521.europe-west2.run.app |
| API via Firebase | https://api.tood.uk |
| GCP Console | https://console.cloud.google.com/run?project=tood-os |
| GitHub | https://github.com/honeybpay-design/TOOD-OS |
| Stripe Dashboard | https://dashboard.stripe.com |

## ไฟล์สำคัญ

| ไฟล์ | หน้าที่ |
|------|---------|
| `apps/api/app/routes_oauth.py` | OAuth callback handler, สร้าง session token |
| `apps/web/app/auth/google/callback/route.ts` | Next.js proxy ของ callback |
| `apps/web/app/dashboard/page.tsx` | อ่าน session_token จาก URL/sessionStorage |
| `apps/web/next.config.ts` | Firebase/Next.js rewrites |
| `firebase.json` | Firebase Hosting routing rules |
| `infra/cloudrun/api.yaml` | Cloud Run API service definition |
| `.env` | Local dev + production secrets (ไม่ commit) |

---

*บันทึกโดย Kiro — 17 October 2026, 07:40 GMT (London)*
