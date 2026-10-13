import type { Metadata } from 'next';
import { DM_Serif_Display, Inter } from 'next/font/google';
import './globals.css';

const dmSerif = DM_Serif_Display({
  weight: '400',
  style: ['normal', 'italic'],
  subsets: ['latin'],
  variable: '--font-dm-serif',
  display: 'swap',
});

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'TOOD — Trusted Operations & Organised Documents',
  description:
    'AI-powered tender writing for UK public sector. Extract requirements, draft answers, and export compliant submissions.',
  icons: {
    icon: '/tood logo icon.ico',
  },
  openGraph: {
    title: 'TOOD — Trusted Operations & Organised Documents',
    description:
      'AI-powered tender writing for UK public sector. Extract requirements, draft answers, and export compliant submissions.',
    url: 'https://tood.uk',
    siteName: 'TOOD',
    locale: 'en_GB',
    type: 'website',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en-GB"
      className={`${dmSerif.variable} ${inter.variable} h-full`}
    >
      <body className="min-h-full flex flex-col bg-[#F8F6F1] text-[#1C1917]">{children}</body>
    </html>
  );
}
