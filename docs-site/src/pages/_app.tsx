import type { AppProps } from 'next/app';
import '../styles/globals.css';
import 'prismjs/themes/prism-tomorrow.css';

export default function App({ Component, pageProps }: AppProps) {
  return <Component {...pageProps} />;
}
