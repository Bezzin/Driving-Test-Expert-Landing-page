import { Sidebar } from '@/components/dashboard/sidebar'
import { LogoutButton } from '@/components/dashboard/logout-button'

export default function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  const dryRun = process.env.DRY_RUN === 'true'

  return (
    <div className="flex min-h-screen">
      <Sidebar dryRun={dryRun} />

      <div className="ml-60 flex flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b bg-background/95 px-6 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <h2 className="text-lg font-semibold text-foreground">Dashboard</h2>
          <LogoutButton />
        </header>

        <main className="flex-1 px-6 py-6">
          <div className="mx-auto max-w-7xl">{children}</div>
        </main>
      </div>
    </div>
  )
}
