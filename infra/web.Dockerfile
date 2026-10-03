FROM node:22-alpine
WORKDIR /app
COPY apps/web/package*.json ./
RUN npm ci
COPY apps/web ./
ARG PAKDATA_API_URL=http://api:8000
ENV PAKDATA_API_URL=$PAKDATA_API_URL
RUN npm run build
USER node
EXPOSE 3000
CMD ["npm","start"]
