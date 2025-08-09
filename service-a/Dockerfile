FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json* yarn.lock* ./
RUN if [ -f yarn.lock ]; then yarn --frozen-lockfile; elif [ -f package-lock.json ]; then npm ci; else npm install; fi
COPY . .
CMD ["node", "index.js"]


