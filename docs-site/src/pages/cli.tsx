import Layout from '../components/Layout';
import GlassCard from '../components/GlassCard';
import CodeBlock from '../components/CodeBlock';

export default function CliPage() {
  return (
    <Layout>
      <h1>CLI Usage</h1>
      <GlassCard title="Common Commands">
        <CodeBlock language="bash" code={`python3 forge.py workspace/example/problem.txt --provider ark\npython3 forge.py workspace/example/problem.txt --num-cases 80\npython3 forge.py workspace/example/problem.txt --skip-run\npython3 forge.py workspace/example/problem.txt --no-generate-solution --solution-path ./solution.cpp`} />
      </GlassCard>
      <GlassCard title="Key Options">
        <ul>
          <li><code>--provider</code>: ark | openai</li>
          <li><code>--num-cases</code>: total number of test files</li>
          <li><code>--timeout</code>: per case limit in seconds</li>
          <li><code>--no-generate-solution</code>: use local solution</li>
        </ul>
      </GlassCard>
    </Layout>
  );
}
