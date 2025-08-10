import fetch from "node-fetch";

const DATA_COLLECTOR_URL =
  process.env.DATA_COLLECTOR_URL || "http://data-collector:4000";
const ERROR_ONLY = process.env.ERROR_ONLY === "1";
const ERROR_PROB = Number.isFinite(Number(process.env.ERROR_PROB))
  ? Number(process.env.ERROR_PROB)
  : 0.3;

const chooseEndpoint = () => {
  if (ERROR_ONLY) return "/api/error";

  const endpoints = [
    "/api/data",
    "/api/error",
    "/api/users",
    "/api/orders",
    "/api/admin",
    "/api/gateway",
    "/api/nonexistent", // This will generate 404s
  ];

  const weights = [0.3, 0.15, 0.2, 0.15, 0.05, 0.1, 0.05]; // Probabilities for each endpoint
  const rand = Math.random();
  let cumulative = 0;

  for (let i = 0; i < endpoints.length; i++) {
    cumulative += weights[i];
    if (rand < cumulative) {
      return endpoints[i];
    }
  }

  return "/api/data"; // fallback
};

const callThroughCollector = async () => {
  const endpoint = chooseEndpoint();
  const url = `${DATA_COLLECTOR_URL}/forward/service-b${endpoint}`;

  // Occasionally make POST requests to /api/users
  const method =
    endpoint === "/api/users" && Math.random() < 0.3 ? "POST" : "GET";

  try {
    const options = {
      method,
      headers: { "Content-Type": "application/json" },
    };

    if (method === "POST") {
      options.body = JSON.stringify({
        name: `user_${Math.floor(Math.random() * 1000)}`,
        email: `user${Math.floor(Math.random() * 1000)}@example.com`,
      });
    }

    const res = await fetch(url, options);
    const text = await res.text();
    console.log(
      `service-a → collector → service-b ${method} ${endpoint} => ${res.status} ${text}`
    );
  } catch (err) {
    console.error("service-a request failed:", err.message);
  }
};

setInterval(callThroughCollector, 2000);
console.log("service-a started sending traffic every 2 seconds");
