import Layout from '../components/Layout';
import GlassCard from '../components/GlassCard';

export default function ArchitecturePage() {
  return (
    <Layout>
      <h1>Architecture</h1>
      <div className="grid">
        <GlassCard title="LLM Module">
          <p>Handles provider selection, API credentials, model defaults, and chat completion calls.</p>
        </GlassCard>
        <GlassCard title="Generator Module">
          <p>Builds prompt for `generate.py` and enforces layered case generation.</p>
        </GlassCard>
        <GlassCard title="Runner Module">
          <p>Executes generator, compiles solution, runs all cases with timeout safety.</p>
        </GlassCard>
        <GlassCard title="Workspace System">
          <p>Stores generated scripts and all `.in/.out` artifacts in a reproducible folder layout.</p>
        </GlassCard>
      </div>
    </Layout>
  );
}
