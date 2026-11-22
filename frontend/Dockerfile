FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci && cp package-lock.json node_modules/.lock-stamp

COPY docker-entrypoint.sh /usr/local/bin/web-entrypoint.sh
COPY . .

EXPOSE 5173
ENTRYPOINT ["sh", "/usr/local/bin/web-entrypoint.sh"]
CMD ["npm", "run", "dev"]
