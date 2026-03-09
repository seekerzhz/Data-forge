import Link from 'next/link';
import { useRouter } from 'next/router';

const navItems = [
  { href: '/', label: 'Homepage' },
  { href: '/quickstart', label: 'Quick Start' },
  { href: '/architecture', label: 'Architecture' },
  { href: '/prompt-system', label: 'Prompt System' },
  { href: '/cli', label: 'CLI Usage' },
  { href: '/roadmap', label: 'Roadmap' }
];

export default function Sidebar() {
  const router = useRouter();

  return (
    <aside className="sidebar glass">
      <h3>Documentation</h3>
      <ul>
        {navItems.map((item) => (
          <li key={item.href}>
            <Link href={item.href} className={router.pathname === item.href ? 'active' : ''}>
              {item.label}
            </Link>
          </li>
        ))}
      </ul>
    </aside>
  );
}
