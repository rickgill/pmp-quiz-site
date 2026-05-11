FROM node:22-bookworm-slim

WORKDIR /app

COPY package.json ./
COPY server.js ./
COPY public ./public
COPY data ./data

EXPOSE 3040

CMD ["node", "server.js"]
