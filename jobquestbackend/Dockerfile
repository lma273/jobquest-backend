# =============================
# Stage 1: Build the Spring Boot app
# =============================
FROM maven:3.9.6-eclipse-temurin-17 AS builder

# Đặt đúng thư mục có pom.xml
WORKDIR /app

ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# Copy toàn bộ project con vào container
COPY . .

# Build application (skip tests)
RUN mvn clean package -DskipTests


# =============================
# Stage 2: Run the app
# =============================
FROM eclipse-temurin:17-jdk-alpine


WORKDIR /app

RUN apk add --no-cache ca-certificates && update-ca-certificates

# Copy jar từ builder stage
COPY --from=builder /app/target/*.jar app.jar

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]



