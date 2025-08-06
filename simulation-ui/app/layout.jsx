import "./globals.css"

export const metadata = {
  title: "Digital Twin Simulation",
  description: "Interactive hierarchical digital twin simulation with predictive replica placement",
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
