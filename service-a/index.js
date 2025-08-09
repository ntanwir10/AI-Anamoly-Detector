import fetch from 'node-fetch';

const DATA_COLLECTOR_URL = process.env.DATA_COLLECTOR_URL || 'http://data-collector:4000';
const ERROR_ONLY = process.env.ERROR_ONLY === '1';
const ERROR_PROB = Number.isFinite(Number(process.env.ERROR_PROB)) ? Number(process.env.ERROR_PROB) : 0.3;

const chooseEndpoint = () => {
  if (ERROR_ONLY) return '/api/error';
  const isError = Math.random() < ERROR_PROB;
  return isError ? '/api/error' : '/api/data';
};

const callThroughCollector = async () => {
  const endpoint = chooseEndpoint();
  const url = `${DATA_COLLECTOR_URL}/forward/service-b${endpoint}`;
  try {
    const res = await fetch(url, { method: 'GET' });
    const text = await res.text();
    console.log(`service-a → collector → service-b ${endpoint} => ${res.status} ${text}`);
  } catch (err) {
    console.error('service-a request failed:', err.message);
  }
};

setInterval(callThroughCollector, 2000);
console.log('service-a started sending traffic every 2 seconds');


