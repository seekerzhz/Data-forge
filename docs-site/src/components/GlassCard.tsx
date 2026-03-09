import { PropsWithChildren } from 'react';

type GlassCardProps = PropsWithChildren<{
  title?: string;
  className?: string;
}>;

export default function GlassCard({ title, className = '', children }: GlassCardProps) {
  return (
    <section className={`glass card ${className}`}>
      {title ? <h2>{title}</h2> : null}
      {children}
    </section>
  );
}
