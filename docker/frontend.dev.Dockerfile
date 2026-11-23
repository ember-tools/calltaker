FROM node:24-slim

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci

EXPOSE 5173
CMD ["npx", "vite", "--host", "0.0.0.0", "--port", "5173"]
