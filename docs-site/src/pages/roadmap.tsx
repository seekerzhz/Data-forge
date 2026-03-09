import Layout from '../components/Layout';
import GlassCard from '../components/GlassCard';

export default function RoadmapPage() {
  return (
    <Layout>
      <h1>Roadmap</h1>
      <GlassCard title="Near-term">
        <ul>
          <li>Judge adapters (Codeforces / AtCoder style)</li>
          <li>Template library for classic data patterns</li>
          <li>Better sandboxed execution metrics</li>
        </ul>
      </GlassCard>
      <GlassCard title="Mid-term">
        <ul>
          <li>Web dashboard for batch generation jobs</li>
          <li>Benchmark reports and flame charts</li>
          <li>Prompt versioning + A/B quality scoring</li>
        </ul>
      </GlassCard>
    </Layout>
  );
}
