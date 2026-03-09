import Layout from '../components/Layout';
import GlassCard from '../components/GlassCard';
import CodeBlock from '../components/CodeBlock';

export default function QuickStartPage() {
  return (
    <Layout>
      <h1>Quick Start</h1>
      <GlassCard title="Install">
        <CodeBlock language="bash" code={`pip install dataforge`} />
      </GlassCard>
      <GlassCard title="Run">
        <CodeBlock language="bash" code={`forge run problem.txt`} />
      </GlassCard>
      <GlassCard title="Repository Workflow">
        <CodeBlock language="bash" code={`python3 -m venv venv\nsource venv/bin/activate\npip install -r requirements.txt\npython3 forge.py workspace/example/problem.txt --provider ark --num-cases 50`} />
      </GlassCard>
    </Layout>
  );
}
