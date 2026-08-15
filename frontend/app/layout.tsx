import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Alma — Lead Management',
  description: 'Lead management for attorneys',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="site-shell">{children}</div>
      </body>
    </html>
  );
}
