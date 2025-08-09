import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';

function App() {
  const [status, setStatus] = useState('NORMAL');
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    const ws = new WebSocket(`ws://${window.location.hostname}:8080`);
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      setStatus('ANOMALOUS');
      setLogs((prev) => [...prev, msg.message]);
    };
    return () => ws.close();
  }, []);

  return (
    <div style={{ fontFamily: 'sans-serif', padding: 24 }}>
      <h2>System Health: {status}</h2>
      <h3>Alerts</h3>
      <ul>
        {logs.map((l, i) => (
          <li key={i}>{l}</li>
        ))}
      </ul>
    </div>
  );
}

const root = createRoot(document.getElementById('root'));
root.render(<App />);


