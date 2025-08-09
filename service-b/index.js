import express from 'express';

const app = express();
const port = 3000;

app.get('/api/data', (req, res) => {
  res.status(200).json({ status: 'ok', ts: Date.now() });
});

app.get('/api/error', (req, res) => {
  res.status(500).json({ status: 'error', message: 'Simulated failure', ts: Date.now() });
});

app.listen(port, () => {
  console.log(`service-b listening on port ${port}`);
});


