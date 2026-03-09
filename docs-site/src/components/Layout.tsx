import { PropsWithChildren } from 'react';
import Footer from './Footer';
import Navbar from './Navbar';
import SearchBox from './SearchBox';
import Sidebar from './Sidebar';

export default function Layout({ children }: PropsWithChildren) {
  return (
    <div className="app-bg">
      <Navbar />
      <main className="layout">
        <Sidebar />
        <section className="content">
          <SearchBox />
          {children}
          <Footer />
        </section>
      </main>
    </div>
  );
}
