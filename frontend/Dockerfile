FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install
RUN npm install -g serve

# Copy application code
COPY . .

# Copy and set entrypoint script
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# Build the application
ARG REACT_APP_IS_DEMO
ENV REACT_APP_IS_DEMO=$REACT_APP_IS_DEMO
RUN npm run build

# Expose port
EXPOSE 3000

# Use entrypoint script to ensure dependencies are installed
ENTRYPOINT ["/app/docker-entrypoint.sh"]
