FROM node:18-alpine as build
WORKDIR /app
# Cache deps
COPY ui/chatbot-react/package*.json /app/
RUN npm ci || npm i
# Then copy sources
COPY ui/chatbot-react/ /app
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
