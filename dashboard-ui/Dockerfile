FROM node:20-alpine as build
WORKDIR /app
COPY package.json package-lock.json* yarn.lock* ./
RUN if [ -f yarn.lock ]; then yarn --frozen-lockfile; elif [ -f package-lock.json ]; then npm ci; else npm install; fi
COPY . .
RUN npm run build || yarn build || true

FROM node:20-alpine
WORKDIR /app
COPY --from=build /app /app
ENV PORT=3000
EXPOSE 3000
CMD ["npm", "start"]


