# Use Node.js as base image
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy frontend files
COPY . .

# Install serve for a static web server
RUN npm install -g serve

# Expose port
EXPOSE 3000

# Command to serve the static files
CMD ["serve", "-s", ".", "-l", "3000"]
