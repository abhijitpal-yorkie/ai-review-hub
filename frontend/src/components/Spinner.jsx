import React from 'react';
import { Loader2 } from 'lucide-react';

export default function Spinner({ size = 16, label }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '.5rem' }}>
      <Loader2 size={size} className="spin" />
      {label && <span>{label}</span>}
    </span>
  );
}
