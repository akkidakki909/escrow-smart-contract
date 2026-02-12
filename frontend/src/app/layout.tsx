import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
    title: 'CampusChain — Programmable Campus Wallet',
    description: 'Blockchain-powered campus wallet on Algorand. Fund, spend, and track — no crypto required.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="en">
            <head>
                <link
                    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
                    rel="stylesheet"
                />
            </head>
            <body>{children}</body>
        </html>
    );
}
