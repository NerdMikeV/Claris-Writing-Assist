import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Claris Writing - LinkedIn Content Automation',
  description: 'AI-powered LinkedIn content creation for supply chain professionals',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <nav className="bg-linkedin-primary text-white shadow-lg">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex items-center">
                <a href="/" className="text-xl font-bold">
                  Claris Writing
                </a>
              </div>
              <div className="flex items-center space-x-4">
                <a
                  href="/"
                  className="px-3 py-2 rounded-md text-sm font-medium hover:bg-linkedin-dark transition-colors"
                >
                  Submit Idea
                </a>
                <a
                  href="/review"
                  className="px-3 py-2 rounded-md text-sm font-medium hover:bg-linkedin-dark transition-colors"
                >
                  Review Dashboard
                </a>
              </div>
            </div>
          </div>
        </nav>
        <main className="min-h-screen">{children}</main>
      </body>
    </html>
  )
}
