FROM node:18-alpine
WORKDIR /app
COPY apps/web/package.json .
# RUN npm install # Skipped for skeleton
COPY apps/web .
CMD ["npm", "run", "dev"]
