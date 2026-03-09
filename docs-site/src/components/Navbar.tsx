import Link from 'next/link';

export default function Navbar() {
  return (
    <header className="navbar glass">
      <Link href="/" className="logo">DataForge</Link>
      <nav>
        <Link href="/">Docs</Link>
        <a href="https://github.com/your-org/dataforge" target="_blank" rel="noreferrer">GitHub</a>
      </nav>
    </header>
  );
}
