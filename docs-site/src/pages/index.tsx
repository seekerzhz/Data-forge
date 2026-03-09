import Layout from '../components/Layout';
import GlassCard from '../components/GlassCard';
import CodeBlock from '../components/CodeBlock';

export default function HomePage() {
  return (
    <Layout>
      <h1>DataForge Documentation</h1>
      <p className="lead">Generate contest data, reference solutions, and outputs with one modern CLI workflow.</p>

      <div className="grid">
        <GlassCard title="Project Introduction">
          <p>DataForge automates competitive-programming data production by combining LLM-generated scripts with deterministic local execution.</p>
        </GlassCard>
        <GlassCard title="Feature Highlights">
          <ul>
            <li>Provider support: Ark and OpenAI</li>
            <li>Configurable case count and distributions</li>
            <li>Per-case timeout protection</li>
            <li>Bring-your-own `solution.cpp` support</li>
          </ul>
        </GlassCard>
      </div>

      <GlassCard title="Architecture Diagram">
        <pre className="diagram">{`Problem Statement
      ↓
  Prompt Engine
      ↓
   LLM Client
   ↙       ↘
generate.py solution.cpp
      ↓          ↓
  Generator   Compiler
      ↓          ↓
    *.in      executable
         ↘   ↙
         Runner
           ↓
         *.out`}</pre>
      </GlassCard>

      <GlassCard title="Installation Steps">
        <CodeBlock language="bash" code={`pip install dataforge\nforge run problem.txt`} />
      </GlassCard>
    </Layout>
  );
}
