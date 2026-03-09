import { useMemo, useState } from 'react';
import Link from 'next/link';

const pages = [
  { title: 'Homepage', href: '/' },
  { title: 'Quick Start', href: '/quickstart' },
  { title: 'Architecture', href: '/architecture' },
  { title: 'Prompt System', href: '/prompt-system' },
  { title: 'CLI Usage', href: '/cli' },
  { title: 'Roadmap', href: '/roadmap' }
];

export default function SearchBox() {
  const [q, setQ] = useState('');
  const results = useMemo(
    () => pages.filter((p) => p.title.toLowerCase().includes(q.toLowerCase())).slice(0, 5),
    [q]
  );

  return (
    <div className="search glass">
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search docs..."
        aria-label="Search docs"
      />
      {q && (
        <div className="search-results">
          {results.map((r) => (
            <Link key={r.href} href={r.href}>{r.title}</Link>
          ))}
          {!results.length && <span>No results</span>}
        </div>
      )}
    </div>
  );
}
