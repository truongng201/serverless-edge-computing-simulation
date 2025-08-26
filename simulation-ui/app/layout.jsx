import "./globals.css"

export const metadata = {
  title: "Serverless Edge Simulation",
  description: "Interactive hierarchical serverless edge simulation with predictive replica placement",
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
