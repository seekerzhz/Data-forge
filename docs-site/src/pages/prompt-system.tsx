import Layout from '../components/Layout';
import GlassCard from '../components/GlassCard';
import CodeBlock from '../components/CodeBlock';

export default function PromptSystemPage() {
  return (
    <Layout>
      <h1>Prompt System</h1>
      <GlassCard title="Generator Prompt Goals">
        <ul>
          <li>Strictly follow input constraints</li>
          <li>Layered cases: small / special / random / max</li>
          <li>Deterministic generation with fixed seed</li>
        </ul>
      </GlassCard>
      <GlassCard title="Solution Prompt Goals">
        <ul>
          <li>Accepted-quality C++17 implementation</li>
          <li>tourist-like concise style</li>
          <li>Brief Chinese comments for key logic</li>
        </ul>
      </GlassCard>
      <GlassCard title="Prompt Template Snippet">
        <CodeBlock language="bash" code={`Given the problem statement below, generate a complete runnable generate.py script...\nOutput Python code only.`} />
      </GlassCard>
    </Layout>
  );
}
