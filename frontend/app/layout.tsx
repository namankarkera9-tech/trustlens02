import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TrustLens AI — Evidence-led media review",
  description: "Inspect suspicious images and short videos through transparent, multi-source evidence review.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return <html lang="en"><body>{children}</body></html>;
}
