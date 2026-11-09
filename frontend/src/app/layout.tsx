import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Nyayavarta - न्यायवार्ता | Multilingual Legal Assistant',
  description:
    'Access legal aid in your regional language. Map old Indian laws to new laws, fill legal applications, and get legal guidance.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
