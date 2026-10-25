import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'tood.os — Every word in your bid, accounted for',
  description:
    'tood.os reads the whole tender pack, verifies every requirement against its source by code, and drafts answers where every sentence records who wrote it, which model, what evidence and who approved it.',
  icons: {
    icon: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect x='4' y='4' width='24' height='24' rx='5' fill='none' stroke='%2314161a' stroke-width='2.4'/%3E%3Cpath d='M10 12h12M10 17h7' stroke='%2314161a' stroke-width='2.4' stroke-linecap='round'/%3E%3Ccircle cx='21.5' cy='21.5' r='3' fill='%230a7a5a'/%3E%3C/svg%3E",
  },
  openGraph: {
    title: 'tood.os — Every word in your bid, accounted for',
    description:
      'Verifiable, evidence-bound AI for UK SMEs bidding for public contracts under the Procurement Act 2023.',
    url: 'https://tood.uk',
    siteName: 'tood.os',
    locale: 'en_GB',
    type: 'website',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-GB" data-theme="dark">
      <head>
        <link rel="preconnect" href="https://api.fontshare.com" crossOrigin="" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://api.fontshare.com/v2/css?f[]=cabinet-grotesk@500,700,800&display=swap"
          rel="stylesheet"
        />
        <link
          href="https://api.fontshare.com/v2/css?f[]=switzer@400,500,600,700&display=swap"
          rel="stylesheet"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              '@context': 'https://schema.org',
              '@type': 'SoftwareApplication',
              name: 'tood.os',
              applicationCategory: 'BusinessApplication',
              description: 'Verifiable, evidence-bound AI workspace for UK public-sector tenders.',
              offers: { '@type': 'Offer', price: '0', priceCurrency: 'GBP' },
            }),
          }}
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
