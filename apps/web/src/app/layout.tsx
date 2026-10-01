import type { Metadata } from 'next'; import './globals.css';
export const metadata: Metadata = {title:'Pakistan Data Platform',description:'Traceable public data, economic intelligence and geographic analytics for Pakistan.'};
export default function Layout({children}:{children:React.ReactNode}) {return <html lang="en"><body>{children}</body></html>}
