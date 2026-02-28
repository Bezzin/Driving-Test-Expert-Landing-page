import type { Metadata } from "next"
import { Sidebar } from "@/components/sidebar"
import { Header } from "@/components/header"
import { QueryProvider } from "@/lib/query-provider"
import "./globals.css"

export const metadata: Metadata = {
  title: "Airees",
  description: "Multi-agent platform",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-gray-950 text-gray-100 antialiased">
        <QueryProvider>
          <Sidebar />
          <div className="lg:pl-64">
            <Header />
            <main className="p-6">{children}</main>
          </div>
        </QueryProvider>
      </body>
    </html>
  )
}
